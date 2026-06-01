"""Password reset token repository."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken
from app.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class PasswordResetRepository(BaseRepository[PasswordResetToken]):
    """Data access layer for PasswordResetToken records."""

    def __init__(self) -> None:
        super().__init__(PasswordResetToken)

    async def get_valid_token(
        self, session: AsyncSession, token_hash: str
    ) -> PasswordResetToken | None:
        """
        Fetch a reset token by its SHA-256 hash that is:
        - Not yet used
        - Not expired

        Returns None if no valid token exists (do NOT reveal whether the token
        exists but is expired vs. was never issued — same UX for both cases).
        """
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.is_used == False,  # noqa: E712
                    PasswordResetToken.expires_at > now,
                )
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(
        self, session: AsyncSession, token_id: UUID
    ) -> bool:
        """Invalidate a token after it has been used."""
        result = await session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(is_used=True)
            .returning(PasswordResetToken.id)
        )
        affected = result.scalar_one_or_none()
        await session.flush()
        return affected is not None

    async def invalidate_all_for_user(
        self, session: AsyncSession, user_id: UUID
    ) -> int:
        """
        Mark all outstanding reset tokens for a user as used.

        Called after a successful password reset to prevent reuse of
        any previously issued tokens.
        """
        result = await session.execute(
            update(PasswordResetToken)
            .where(
                and_(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.is_used == False,  # noqa: E712
                )
            )
            .values(is_used=True)
            .returning(PasswordResetToken.id)
        )
        count = len(result.all())
        await session.flush()
        return count

    async def cleanup_expired(self, session: AsyncSession) -> int:
        """Hard-delete expired password reset tokens (maintenance)."""
        now = datetime.now(timezone.utc)
        result = await session.execute(
            delete(PasswordResetToken)
            .where(PasswordResetToken.expires_at < now)
            .returning(PasswordResetToken.id)
        )
        count = len(result.all())
        await session.flush()
        return count


password_reset_repository = PasswordResetRepository()
