"""
Authentication routes — /v1/auth/*

All routes are intentionally thin:
  - Parse request body using Pydantic schemas
  - Extract request metadata (IP, User-Agent)
  - Call auth_service for business logic
  - Set/clear HttpOnly cookies
  - Return standard response envelope

Route handlers do NOT contain business logic.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import (
    LOGIN_RATE_LIMIT,
    PASSWORD_RESET_RATE_LIMIT,
    REGISTER_RATE_LIMIT,
    limiter,
)
from app.db.session import get_async_session
from app.dependencies import get_current_user, get_session_id
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RegisterRequest,
    RegisterResponse,
    TokenRefreshResponse,
)
from app.schemas.common import SuccessResponse
from app.config import settings
from app.services.auth_service import auth_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set HttpOnly, Secure, SameSite=None cookies for both tokens.

    SameSite=None is required because the frontend and backend are served from
    different origins (cross-site). SameSite=Strict would silently block cookies
    on all cross-origin requests. SameSite=None requires Secure=True (HTTPS),
    which is enforced by settings.cookie_secure in production.
    """
    cookie_kwargs = {
        "httponly": True,
        "secure": settings.cookie_secure,  # Must be True in production (HTTPS required for SameSite=None)
        "samesite": "none",                # Cross-origin: frontend and backend on different domains
        "path": "/",
    }
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_seconds,
        **cookie_kwargs,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_expire_seconds,
        **cookie_kwargs,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Remove auth cookies on logout."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def _get_client_ip(request: Request) -> str | None:
    """Extract real client IP, handling reverse-proxy X-Forwarded-For."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


# ── POST /auth/register ────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=SuccessResponse[RegisterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit(REGISTER_RATE_LIMIT)
async def register(
    request: Request,
    body: RegisterRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SuccessResponse[RegisterResponse]:
    """
    Create a new user account.

    - Validates username uniqueness and password strength.
    - Hashes the password with bcrypt.
    - Does NOT auto-login; client must call /login after registration.
    """
    data = await auth_service.register_user(
        session=session,
        full_name=body.full_name,
        username=body.username,
        password=body.password,
    )
    return SuccessResponse(
        data=data,
        message="Account created successfully. Please log in.",
    )


# ── POST /auth/login ───────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=SuccessResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive session cookies",
)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SuccessResponse[LoginResponse]:
    """
    Authenticate with username + password.

    Sets HttpOnly cookies:
    - access_token: short-lived JWT (15 min)
    - refresh_token: long-lived opaque token (30 days)

    The response body includes Gmail connection status to drive
    the frontend post-login routing (onboarding vs. dashboard).
    """
    user_response, access_token, refresh_token, _session_id = (
        await auth_service.login_user(
            session=session,
            username=body.username,
            password=body.password,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return SuccessResponse(
        data=LoginResponse(user=user_response),
        message="Login successful",
    )


# ── POST /auth/logout ──────────────────────────────────────────────────────────
@router.post(
    "/logout",
    response_model=SuccessResponse[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke session and clear cookies",
)
async def logout(
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    session_id: UUID = Depends(get_session_id),
) -> SuccessResponse[MessageResponse]:
    """
    Log out by revoking the current session and clearing auth cookies.

    The session_id is extracted from the JWT access token payload (sid claim).
    Even if the access token has expired, the refresh flow should be used first.
    """
    await auth_service.logout_user(session=session, session_id=session_id)
    _clear_auth_cookies(response)
    return SuccessResponse(data=MessageResponse(message="Logged out successfully"))


# ── POST /auth/refresh ─────────────────────────────────────────────────────────
@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenRefreshResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using refresh token cookie",
)
async def refresh_token(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
) -> SuccessResponse[TokenRefreshResponse]:
    """
    Rotate the refresh token and issue a new access token.

    Reads both access_token (for session_id) and refresh_token cookies.
    Both are rotated (new cookies set on response).

    This endpoint intentionally does NOT require get_current_user because
    the access token may already be expired when this is called.
    """
    from fastapi import Cookie
    from app.core.exceptions import UnauthorizedException

    access_token: str | None = request.cookies.get("access_token")
    raw_refresh_token: str | None = request.cookies.get("refresh_token")

    if not raw_refresh_token:
        raise UnauthorizedException()

    # Extract session_id from access token (may be expired — decode ignores exp)
    session_id = await _extract_session_id_lenient(access_token)
    if not session_id:
        raise UnauthorizedException()

    new_access, new_refresh, _new_sid = await auth_service.refresh_tokens(
        session=session,
        session_id=session_id,
        raw_refresh_token=raw_refresh_token,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    _set_auth_cookies(response, new_access, new_refresh)
    return SuccessResponse(data=TokenRefreshResponse())


async def _extract_session_id_lenient(access_token: str | None) -> UUID | None:
    """
    Extract session ID from JWT without verifying expiry.

    Used ONLY for the refresh endpoint where the access token may be expired.
    We still verify the signature — just skip exp validation.
    """
    if not access_token:
        return None
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(
            access_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        sid_str = payload.get("sid")
        return UUID(sid_str) if sid_str else None
    except Exception:
        return None


# ── POST /auth/forgot-password ─────────────────────────────────────────────────
@router.post(
    "/forgot-password",
    response_model=SuccessResponse[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Request a password reset email",
)
@limiter.limit(PASSWORD_RESET_RATE_LIMIT)
async def forgot_password(
    request: Request,
    body: PasswordResetRequestSchema,
    session: AsyncSession = Depends(get_async_session),
) -> SuccessResponse[MessageResponse]:
    """
    Send a password reset link to the user's connected Gmail.

    Always returns the same response to prevent user enumeration.
    The actual email is only sent if the user exists AND has a connected Gmail.
    """
    await auth_service.request_password_reset(
        session=session,
        username=body.username,
    )
    return SuccessResponse(
        data=MessageResponse(
            message=(
                "If that username exists and has a connected Gmail account, "
                "a password reset link has been sent."
            )
        )
    )


# ── POST /auth/reset-password ──────────────────────────────────────────────────
@router.post(
    "/reset-password",
    response_model=SuccessResponse[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Complete password reset using the emailed token",
)
async def reset_password(
    body: PasswordResetConfirmSchema,
    session: AsyncSession = Depends(get_async_session),
) -> SuccessResponse[MessageResponse]:
    """
    Reset the user's password using the single-use token from the reset email.

    On success:
    - Password is updated.
    - All sessions are revoked (user must re-login everywhere).
    - All outstanding reset tokens for this user are invalidated.
    """
    await auth_service.confirm_password_reset(
        session=session,
        raw_token=body.token,
        new_password=body.new_password,
    )
    return SuccessResponse(
        data=MessageResponse(
            message="Password reset successfully. Please log in with your new password."
        )
    )
