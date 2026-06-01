"""
Shared FastAPI dependency functions.

All dependencies that are reused across multiple route modules live here:
  - get_current_user: decode JWT from cookie, return User model.
  - get_session_id: extract session ID from the JWT payload.
  - optional_current_user: like get_current_user but returns None if unauthenticated.

Design:
  - Tokens are read from HttpOnly cookies, NOT Authorization headers.
  - The JWT payload contains the user_id (sub) and session_id (sid).
  - We do NOT hit the database on every request just to validate the JWT —
    JWT validation is stateless. We only hit the DB for:
      a) Explicit session checks (token refresh, logout).
      b) Loading the full User object when the route needs it.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import Cookie, Depends, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenException, UnauthorizedException
from app.core.security import decode_access_token
from app.db.session import get_async_session
from app.models.user import User
from app.repositories.user_repository import user_repository

logger = structlog.get_logger(__name__)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    access_token: str | None = Cookie(default=None),
) -> User:
    """
    Dependency: return the authenticated User for the current request.

    Reads the access_token cookie, validates the JWT, and loads the User
    from the database. Raises UnauthorizedException if:
    - Cookie is missing
    - JWT is invalid or expired
    - User is not found or is inactive
    """
    if not access_token:
        raise UnauthorizedException()

    try:
        payload = decode_access_token(access_token)
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise InvalidTokenException()
        user_id = UUID(user_id_str)
    except (JWTError, ValueError) as exc:
        logger.debug("jwt_decode_failed", error=str(exc))
        raise InvalidTokenException() from exc

    user = await user_repository.get_active_by_id(session, user_id)
    if not user:
        raise UnauthorizedException()

    # Bind user context to logs for this request
    import structlog.contextvars
    structlog.contextvars.bind_contextvars(
        user_id=str(user.id),
        username=user.username,
    )

    return user


async def get_session_id(
    access_token: str | None = Cookie(default=None),
) -> UUID:
    """
    Dependency: extract the session ID (sid) from the access token JWT.

    Used by logout and refresh endpoints which need to target a specific session.
    """
    if not access_token:
        raise UnauthorizedException()

    try:
        payload = decode_access_token(access_token)
        sid_str: str | None = payload.get("sid")
        if not sid_str:
            raise InvalidTokenException(message="Session ID missing from token")
        return UUID(sid_str)
    except (JWTError, ValueError) as exc:
        raise InvalidTokenException() from exc


async def get_optional_user(
    session: AsyncSession = Depends(get_async_session),
    access_token: str | None = Cookie(default=None),
) -> User | None:
    """
    Dependency: return the current user OR None if not authenticated.

    For endpoints that behave differently for authenticated vs anonymous users.
    """
    if not access_token:
        return None
    try:
        return await get_current_user(
            request=None,  # type: ignore[arg-type]
            session=session,
            access_token=access_token,
        )
    except Exception:
        return None


async def require_gmail_connected(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """
    Dependency: ensure the current user has an active Gmail connection.
    Used for routes that interact with Gmail (e.g. sync, complete onboarding).
    """
    from app.repositories.gmail_repository import gmail_repository
    
    gmail = await gmail_repository.get_connection(session, user.id)
    if not gmail:
        raise UnauthorizedException(message="Gmail connection required.")
    return user


async def require_onboarding_completed(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependency: ensure the current user has completed full onboarding.
    Gates access to platform features like Dashboard, Analytics, etc.
    """
    if not user.is_onboarding_completed:
        raise UnauthorizedException(message="Onboarding incomplete. Please finish setting up your account.")
    return user
