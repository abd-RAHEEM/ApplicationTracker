"""
Gmail OAuth service layer.

Handles:
1. Generating the Google OAuth authorization URL.
2. Exchanging the authorization code for tokens.
3. Fetching the user's Gmail profile to get the verified email address.
4. Encrypting the refresh token and storing it in the database.
5. Emitting the is_email_verified=True signal to the User model.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.oauth_state import create_oauth_state_token, verify_oauth_state_token
from app.core.security import encrypt_text
from app.repositories.gmail_repository import gmail_repository
from app.repositories.user_repository import user_repository

logger = structlog.get_logger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/gmail/v1/users/me/profile"

# Scopes: Read-only access to Gmail (as specified). No Send/Modify/Delete.
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailOAuthService:
    """Business logic for Gmail OAuth flow."""

    async def get_authorization_url(
        self,
        session: AsyncSession,
        user_id: UUID,
        frontend_url: str | None = None,
    ) -> str:
        """
        Generate the Google OAuth consent screen URL.
        
        Rejects initiation if the user already has a Gmail connection.
        Injects a signed JWT as the 'state' parameter for CSRF protection.
        Requests offline access to guarantee a refresh token is issued.
        """
        # Enforce permanent identity: Reject if already connected
        existing_conn = await gmail_repository.get_connection(session, user_id)
        if existing_conn:
            raise BadRequestException(message="A Gmail account is already permanently linked to this profile. Account switching is not supported.")

        if not settings.google_client_id or not settings.google_redirect_uri:
            raise RuntimeError("Google OAuth configuration is missing in environment variables.")

        state_token = create_oauth_state_token(user_id, frontend_url)
        
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "state": state_token,
            "access_type": "offline",
            "prompt": "consent",  # Force consent to ensure refresh token is returned
        }
        
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        logger.info("gmail_oauth_url_generated", user_id=str(user_id))
        return url

    async def handle_oauth_callback(
        self,
        session: AsyncSession,
        user_id: UUID,
        code: str,
        state: str,
    ) -> None:
        """
        Handle the redirect from Google, exchange code for tokens, and persist.

        Steps:
        1. Verify state CSRF token.
        2. Exchange code for access + refresh tokens.
        3. Fetch the verified Gmail address from Google API.
        4. Encrypt the refresh token.
        5. Upsert GmailConnection record.
        6. Mark User.is_email_verified = True.
        """
        if not settings.google_client_id or not settings.google_client_secret:
            raise RuntimeError("Google OAuth configuration is missing.")

        # 0. Enforce permanent identity: check if already connected
        existing_conn = await gmail_repository.get_connection(session, user_id)
        if existing_conn:
            raise BadRequestException(message="A Gmail account is already permanently linked to this profile.")

        # 1. Verify CSRF state token
        verify_oauth_state_token(state, user_id)
        
        # 2. Exchange code for tokens
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.google_redirect_uri,
                },
            )
            
            if token_res.status_code != 200:
                logger.error("google_token_exchange_failed", response=token_res.text)
                raise BadRequestException(message="Failed to exchange authorization code.")
                
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3599)
            granted_scopes = token_data.get("scope", "").split(" ")
            
            if not access_token or not refresh_token:
                logger.error("google_missing_refresh_token", user_id=str(user_id))
                raise BadRequestException(
                    message="Google did not return a refresh token. You must re-authenticate and consent to offline access."
                )
                
            # 3. Fetch user's Gmail profile to get their email address
            profile_res = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if profile_res.status_code != 200:
                logger.error("google_profile_fetch_failed", response=profile_res.text)
                raise BadRequestException(message="Failed to fetch Gmail profile.")
                
            profile_data = profile_res.json()
            gmail_email = profile_data.get("emailAddress")
            
            if not gmail_email:
                raise BadRequestException(message="Google profile did not contain an email address.")

        # 4. Encrypt the refresh token
        encrypted_refresh = encrypt_text(refresh_token)
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        # 5. Create permanent Gmail connection
        await gmail_repository.create_connection(
            session=session,
            user_id=user_id,
            gmail_email=gmail_email,
            encrypted_refresh_token=encrypted_refresh,
            token_expiry=token_expiry,
            scopes=granted_scopes,
        )
        
        # 6. Mark user email as verified (this is the core verification event)
        await user_repository.mark_email_verified(session, user_id)
        
        logger.info(
            "gmail_oauth_completed",
            user_id=str(user_id),
            gmail_email=gmail_email,
        )

    async def complete_onboarding(
        self, session: AsyncSession, user_id: UUID, import_range: str, import_from: datetime
    ) -> None:
        """
        Mark initial import configuration as complete and save the import range/date.
        This signals that the user has fully onboarded and unlocks the platform.
        """
        updated_conn = await gmail_repository.complete_initial_import_config(
            session, user_id, import_range, import_from
        )
        if not updated_conn:
            raise BadRequestException(message="No Gmail connection found.")
            
        # Update user's onboarding completion flag
        await user_repository.mark_onboarding_completed(session, user_id)
        
        logger.info("onboarding_completed", user_id=str(user_id), import_range=import_range)


gmail_oauth_service = GmailOAuthService()
