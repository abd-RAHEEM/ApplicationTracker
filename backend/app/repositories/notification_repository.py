"""Notification repository — in-app notification CRUD."""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class NotificationRepository(BaseRepository[Notification]):
    """Data access layer for Notification records."""

    def __init__(self) -> None:
        super().__init__(Notification)

    async def get_unread_for_user(
        self, session: AsyncSession, user_id: UUID, limit: int = 20
    ) -> list[Notification]:
        """Fetch the most recent unread notifications for a user."""
        result = await session.execute(
            select(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_for_user(
        self, session: AsyncSession, user_id: UUID, limit: int = 50
    ) -> list[Notification]:
        """Fetch all notifications for a user (read + unread), newest first."""
        result = await session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_all_read(
        self, session: AsyncSession, user_id: UUID
    ) -> int:
        """Mark all unread notifications for a user as read."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = await session.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
            .values(is_read=True, read_at=now)
            .returning(Notification.id)
        )
        count = len(result.all())
        await session.flush()
        return count

    async def mark_read(
        self, session: AsyncSession, notification_id: UUID, user_id: UUID
    ) -> bool:
        """Mark a single notification as read (scoped to user for safety)."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = await session.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,  # SECURITY: user scope
                )
            )
            .values(is_read=True, read_at=now)
            .returning(Notification.id)
        )
        affected = result.scalar_one_or_none()
        await session.flush()
        return affected is not None

    async def create_notification(
        self,
        session: AsyncSession,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str | None = None,
        related_entity_id: UUID | None = None,
    ) -> Notification:
        """Helper to create a typed notification record."""
        return await self.create(
            session,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_entity_id=related_entity_id,
        )

    async def unread_count(self, session: AsyncSession, user_id: UUID) -> int:
        """Return count of unread notifications for badge display."""
        return await self.count(session, user_id=user_id, is_read=False)


notification_repository = NotificationRepository()
