"""Session repository — manages refresh token sessions."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession
from app.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class SessionRepository(BaseRepository[UserSession]):
    """Data access layer for UserSession records."""

    def __init__(self) -> None:
        super().__init__(UserSession)

    async def get_valid_session(
        self, session: AsyncSession, session_id: UUID
    ) -> UserSession | None:
        """
        Fetch a session that is not revoked and not expired.

        Used during token refresh to validate the incoming refresh token.
        """
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(UserSession).where(
                and_(
                    UserSession.id == session_id,
                    UserSession.is_revoked == False,  # noqa: E712
                    UserSession.expires_at > now,
                )
            )
        )
        return result.scalar_one_or_none()

    async def revoke_session(
        self, session: AsyncSession, session_id: UUID
    ) -> bool:
        """Mark a single session as revoked (logout)."""
        result = await session.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(is_revoked=True)
            .returning(UserSession.id)
        )
        affected = result.scalar_one_or_none()
        await session.flush()
        logger.info("session_revoked", session_id=str(session_id))
        return affected is not None

    async def revoke_all_for_user(
        self, session: AsyncSession, user_id: UUID
    ) -> int:
        """
        Revoke ALL active sessions for a user.

        Used when:
        - User changes their password (invalidate all other devices).
        - Account is deactivated.
        - Suspicious activity detected (future).
        """
        result = await session.execute(
            update(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_revoked == False,  # noqa: E712
                )
            )
            .values(is_revoked=True)
            .returning(UserSession.id)
        )
        count = len(result.all())
        await session.flush()
        logger.info("all_sessions_revoked", user_id=str(user_id), count=count)
        return count

    async def cleanup_expired(self, session: AsyncSession) -> int:
        """
        Hard-delete expired sessions (maintenance task).

        Safe to call periodically — expired sessions serve no purpose.
        """
        now = datetime.now(timezone.utc)
        result = await session.execute(
            delete(UserSession)
            .where(UserSession.expires_at < now)
            .returning(UserSession.id)
        )
        count = len(result.all())
        await session.flush()
        if count:
            logger.info("expired_sessions_cleaned", count=count)
        return count


session_repository = SessionRepository()
