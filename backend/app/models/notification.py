"""Notification model — in-app notifications only (no external delivery)."""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(str, enum.Enum):
    """
    Supported in-app notification types.
    Only in-app notifications are implemented (Q6 decision).
    """

    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    NEW_APPLICATION = "new_application"
    NEW_INTERVIEW = "new_interview"
    NEW_OFFER = "new_offer"
    DASHBOARD_UPDATED = "dashboard_updated"


class Notification(Base, PrimaryKeyMixin, TimestampMixin):
    """
    In-app notification record.

    Design decisions:
    - Stored in DB so notifications persist across page refreshes.
    - SSE broadcasts are the real-time delivery mechanism; this table serves
      as the notification inbox for when the user is not connected via SSE.
    - is_read / read_at track acknowledgment state.
    - related_entity_id allows future deep-linking (e.g., open the specific
      application when clicking a NEW_INTERVIEW notification).
    - No pagination overhead: notifications are user-scoped and volume is low.
    """

    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, name="notification_type", create_type=True),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    related_entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="Optional FK to the relevant application/sync_log for deep-linking",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="notifications", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id!s} type={self.notification_type} "
            f"read={self.is_read}>"
        )
