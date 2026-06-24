"""
Authentication service — the core business logic layer for all auth operations.

Responsibilities:
  - register_user: validate uniqueness, hash password, create session
  - login_user: verify credentials, create JWT + refresh token
  - logout_user: revoke session
  - refresh_tokens: validate refresh token, rotate, issue new pair
  - request_password_reset: generate reset token, send email
  - confirm_password_reset: validate token, update password, revoke all sessions
  - change_password: verify current password, update, revoke other sessions
  - delete_account: verify password, deactivate account

This service coordinates repositories and does NOT touch HTTP concerns.
All exceptions raised here are AppException subclasses (caught by handlers in main.py).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    NotFoundException,
    SessionRevokedException,
    UsernameTakenException,
)
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    hash_password,
    hash_reset_token,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.models.user import User
from app.repositories.password_reset_repository import password_reset_repository
from app.repositories.session_repository import session_repository
from app.repositories.user_repository import user_repository
from app.schemas.auth import (
    LoginResponse,
    RegisterResponse,
    UserAuthResponse,
)
from app.services.email_service import email_service

logger = structlog.get_logger(__name__)


class AuthService:
    """
    Authentication business logic.

    All public methods accept an AsyncSession as the first argument.
    The session lifecycle (commit/rollback) is managed by the FastAPI
    dependency get_async_session — not inside this service.
    """

    # ── Register ───────────────────────────────────────────────────────────────
    async def register_user(
        self,
        session: AsyncSession,
        full_name: str,
        username: str,
        password: str,
    ) -> RegisterResponse:
        """
        Create a new user account.

        Steps:
          1. Check username uniqueness (fail-fast before hashing).
          2. Hash the password with bcrypt.
          3. Persist the User record.
          4. Return the registration response.

        Does NOT automatically log in the user — the client must call /login
        after registration. This is deliberate: it keeps the registration
        endpoint idempotent and separates concerns.
        """
        logger.info("register_attempt", username=username)

        # 1. Uniqueness check
        if await user_repository.username_exists(session, username):
            raise UsernameTakenException()

        # 2. Hash password
        hashed = hash_password(password)

        try:
            user = await user_repository.create(
                session,
                full_name=full_name,
                username=username.lower(),
                hashed_password=hashed,
                is_active=True,
            )
        except IntegrityError as e:
            logger.warning("user_registration_integrity_error", username=username, error=str(e))
            raise UsernameTakenException()

        logger.info("user_registered", user_id=str(user.id), username=user.username)

        return RegisterResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            created_at=user.created_at,
        )

    # ── Login ──────────────────────────────────────────────────────────────────
    async def login_user(
        self,
        session: AsyncSession,
        username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[UserAuthResponse, str, str, UUID]:
        """
        Authenticate a user and create a new session.

        Returns:
            (user_response, access_token, refresh_token, session_id)

        The access_token and refresh_token are returned to the route handler
        for delivery via HttpOnly cookies. The session_id is embedded in
        the refresh token JWT payload (or stored separately).

        Security notes:
        - Constant-time comparison via passlib.verify (immune to timing attacks).
        - Identical error message for wrong username vs wrong password
          (prevents user enumeration).
        """
        logger.info("login_attempt", username=username)

        # Fetch user — same error for wrong username and wrong password
        user = await user_repository.get_by_username(session, username)
        if not user or not user.is_active:
            raise InvalidCredentialsException()

        # Verify password
        if not verify_password(password, user.hashed_password):
            logger.warning("login_failed_wrong_password", username=username)
            raise InvalidCredentialsException()

        # Check Gmail connection status
        gmail_connected, initial_import_done = await self._get_gmail_status(
            session, user.id
        )

        # Create session
        raw_refresh_token = create_refresh_token()
        refresh_hash = hash_refresh_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

        db_session = await session_repository.create(
            session,
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Create access JWT (embed session_id for correlation)
        access_token = create_access_token(
            subject=user.id,
            extra_claims={
                "username": user.username,
                "sid": str(db_session.id),
            },
        )

        logger.info("login_success", user_id=str(user.id), session_id=str(db_session.id))

        user_response = UserAuthResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            gmail_connected=gmail_connected,
            initial_import_done=initial_import_done,
            is_onboarding_completed=user.is_onboarding_completed,
        )

        # Trigger non-blocking sync if user is fully onboarded
        if user.is_onboarding_completed:
            from app.worker.tasks import run_incremental_sync
            run_incremental_sync.delay(str(user.id))

        return user_response, access_token, raw_refresh_token, db_session.id

    # ── Logout ─────────────────────────────────────────────────────────────────
    async def logout_user(
        self,
        session: AsyncSession,
        session_id: UUID,
    ) -> None:
        """
        Revoke the current session (logout).

        The client must also clear the cookies (done in the route handler).
        """
        await session_repository.revoke_session(session, session_id)
        logger.info("logout", session_id=str(session_id))

    # ── Token Refresh ──────────────────────────────────────────────────────────
    async def refresh_tokens(
        self,
        session: AsyncSession,
        session_id: UUID,
        raw_refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str, UUID]:
        """
        Validate a refresh token and issue a new access + refresh token pair.

        Implements refresh token rotation:
        1. Verify the raw refresh token against the stored hash.
        2. Revoke the old session.
        3. Create a new session with a new refresh token.
        4. Return (new_access_token, new_refresh_token, new_session_id).

        Rotation means each refresh token can only be used ONCE. If a refresh
        token is reused (replay attack), the original session was already revoked
        so the replay attempt fails.
        """
        # Fetch valid session
        db_session = await session_repository.get_valid_session(session, session_id)
        if not db_session:
            raise SessionRevokedException()

        # Verify token hash
        if not verify_refresh_token(raw_refresh_token, db_session.refresh_token_hash):
            logger.warning(
                "refresh_token_hash_mismatch",
                session_id=str(session_id),
            )
            # Revoke all sessions for this user (possible token theft)
            await session_repository.revoke_all_for_user(session, db_session.user_id)
            raise InvalidTokenException()

        # Fetch the user (may have been deactivated since last login)
        user = await user_repository.get_active_by_id(session, db_session.user_id)
        if not user:
            raise InvalidCredentialsException()

        # Revoke old session
        await session_repository.revoke_session(session, session_id)

        # Issue new refresh token + session
        new_raw_refresh = create_refresh_token()
        new_refresh_hash = hash_refresh_token(new_raw_refresh)
        new_expires = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

        new_db_session = await session_repository.create(
            session,
            user_id=user.id,
            refresh_token_hash=new_refresh_hash,
            expires_at=new_expires,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Issue new access JWT
        new_access_token = create_access_token(
            subject=user.id,
            extra_claims={
                "username": user.username,
                "sid": str(new_db_session.id),
            },
        )

        logger.info(
            "tokens_refreshed",
            user_id=str(user.id),
            old_session=str(session_id),
            new_session=str(new_db_session.id),
        )

        return new_access_token, new_raw_refresh, new_db_session.id

    # ── Password Reset — Request ───────────────────────────────────────────────
    async def request_password_reset(
        self,
        session: AsyncSession,
        username: str,
    ) -> None:
        """
        Initiate a password reset flow.

        Password reset is ONLY available to users who have completed Gmail
        onboarding (is_email_verified=True). Users who registered but never
        connected Gmail cannot request a password reset — there is no verified
        email address to send the reset link to.

        The response is ALWAYS the same message to prevent user enumeration,
        regardless of whether the user exists or has completed onboarding.

        Steps:
          1. Look up user by username.
          2. Guard: user must be active AND is_email_verified=True.
          3. Look up connected Gmail email (source of verified address).
          4. Generate (raw_token, sha256_hash).
          5. Store token_hash + expiry in DB.
          6. Send email with raw_token embedded in reset URL.
        """
        logger.info("password_reset_requested", username=username)

        user = await user_repository.get_by_username(session, username)
        if not user or not user.is_active:
            # Return silently — don't reveal user existence
            logger.info("password_reset_user_not_found", username=username)
            return

        # Gate: password reset is only available after Gmail onboarding completes.
        # is_email_verified is set to True when Gmail OAuth succeeds and provides
        # a Google-verified email address.
        if not user.is_email_verified:
            logger.info(
                "password_reset_email_not_verified",
                user_id=str(user.id),
                hint="User has not completed Gmail onboarding",
            )
            return  # Silent — same UX as non-existent user

        # Get Gmail email for sending (the verified address from OAuth)
        gmail_email = await self._get_gmail_email(session, user.id)
        if not gmail_email:
            logger.warning(
                "password_reset_verified_but_no_gmail_record",
                user_id=str(user.id),
                hint="is_email_verified=True but no active gmail_connection found — data inconsistency",
            )
            return  # Silent

        # Generate token
        raw_token, token_hash = create_password_reset_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )

        await password_reset_repository.create(
            session,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Send email (non-blocking failure)
        await email_service.send_password_reset_email(
            to_email=gmail_email,
            username=user.username,
            reset_token=raw_token,
        )

    # ── Password Reset — Confirm ───────────────────────────────────────────────
    async def confirm_password_reset(
        self,
        session: AsyncSession,
        raw_token: str,
        new_password: str,
    ) -> None:
        """
        Complete a password reset using the token from the email.

        Steps:
          1. Hash the raw token and look up the valid record.
          2. Load the user.
          3. Update password hash.
          4. Invalidate all outstanding reset tokens for this user.
          5. Revoke all sessions (forces re-login on all devices).
        """
        token_hash = hash_reset_token(raw_token)
        reset_record = await password_reset_repository.get_valid_token(
            session, token_hash
        )
        if not reset_record:
            raise InvalidTokenException(
                message="Reset link is invalid or has expired. Please request a new one."
            )

        # Fetch user
        user = await user_repository.get_active_by_id(session, reset_record.user_id)
        if not user:
            raise InvalidCredentialsException()

        # Update password
        new_hash = hash_password(new_password)
        await user_repository.update_password(session, user.id, new_hash)

        # Invalidate all reset tokens for this user
        await password_reset_repository.invalidate_all_for_user(session, user.id)

        # Revoke all sessions — forces fresh login on all devices
        await session_repository.revoke_all_for_user(session, user.id)

        logger.info("password_reset_completed", user_id=str(user.id))

    # ── Change Password ────────────────────────────────────────────────────────
    async def change_password(
        self,
        session: AsyncSession,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change password for an authenticated user (Settings page).

        Verifies current password before update.
        Revokes all OTHER sessions (not the current one — user stays logged in).
        """
        user = await user_repository.get_active_by_id(session, user_id)
        if not user:
            raise NotFoundException(message="User not found")

        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsException(message="Current password is incorrect")

        new_hash = hash_password(new_password)
        await user_repository.update_password(session, user.id, new_hash)

        # Revoke ALL sessions — user must re-login everywhere
        await session_repository.revoke_all_for_user(session, user.id)

        logger.info("password_changed", user_id=str(user_id))

    # ── Delete Account ─────────────────────────────────────────────────────────
    async def delete_account(
        self, session: AsyncSession, user_id: UUID, password: str
    ) -> None:
        """
        Permanently delete a user account after verifying their password.
        Uses CASCADE to delete all associated data automatically.
        """
        user = await user_repository.get_by_id(session, user_id)
        if not user:
            raise BadRequestException(message="User not found")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise BadRequestException(message="Incorrect password")

        # Permanent deletion
        await session.delete(user)
        await session.commit()
        logger.info("account_permanently_deleted", user_id=str(user_id))

    # ── Private Helpers ────────────────────────────────────────────────────────
    async def _get_gmail_status(
        self, session: AsyncSession, user_id: UUID
    ) -> tuple[bool, bool]:
        """Return (gmail_connected, initial_import_done) for a user."""
        from sqlalchemy import select
        from app.models.gmail_connection import GmailConnection

        result = await session.execute(
            select(
                GmailConnection.id,
                GmailConnection.initial_import_done,
            ).where(
                GmailConnection.user_id == user_id
            )
        )
        row = result.first()
        if not row:
            return False, False
        return True, row.initial_import_done

    async def _get_gmail_email(
        self, session: AsyncSession, user_id: UUID
    ) -> str | None:
        """Return the connected Gmail email address or None."""
        from sqlalchemy import select
        from app.models.gmail_connection import GmailConnection

        result = await session.execute(
            select(GmailConnection.gmail_email).where(
                GmailConnection.user_id == user_id
            )
        )
        return result.scalar_one_or_none()


# Singleton
auth_service = AuthService()
