"""
OAuth State management.

The OAuth 2.0 flow requires a `state` parameter to prevent Cross-Site Request
Forgery (CSRF) attacks.

Design:
  - We use a signed JWT as the state token instead of storing it in the DB or session.
  - The JWT contains the user_id and an expiry time (e.g., 5 minutes).
  - When the OAuth callback returns, we verify the JWT signature and ensure the
    user_id inside matches the currently authenticated user.
  - This guarantees the user who initiated the OAuth flow is the exact same user
    who is completing it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
import structlog

from app.config import settings
from app.core.exceptions import InvalidTokenException

logger = structlog.get_logger(__name__)

# We use the same secret key but a distinct algorithm or prefix could be used.
# For simplicity, we just use a specific claim `type="oauth_state"` to prevent
# this from being used as an access token.


def create_oauth_state_token(user_id: UUID) -> str:
    """Create a short-lived state JWT for the OAuth flow."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=settings.oauth_state_expire_seconds)
    
    payload = {
        "sub": str(user_id),
        "type": "oauth_state",
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_oauth_state_token(token: str, expected_user_id: UUID) -> None:
    """
    Verify the state JWT and ensure it matches the current user.
    Raises InvalidTokenException on failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        
        if payload.get("type") != "oauth_state":
            raise InvalidTokenException(message="Invalid state token type.")
            
        token_user_id = payload.get("sub")
        if not token_user_id or str(expected_user_id) != token_user_id:
            logger.warning(
                "oauth_state_user_mismatch",
                expected_user=str(expected_user_id),
                token_user=token_user_id,
            )
            raise InvalidTokenException(message="State token user mismatch. CSRF protection triggered.")
            
    except JWTError as exc:
        logger.warning("oauth_state_invalid", error=str(exc))
        raise InvalidTokenException(message="Invalid or expired state token.") from exc
