"""SyncLog model — per-sync audit record."""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class SyncType(str, enum.Enum):
    INITIAL_IMPORT = "initial_import"
    INCREMENTAL = "incremental"
    MANUAL = "manual"


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncLog(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Records every sync operation with statistics and outcome.

    Design decisions:
    - One row per sync run. Used for SSE status queries and audit history.
    - celery_task_id links to the Celery task so frontend can poll status
      if the SSE connection drops.
    - Statistics (emails_fetched, emails_parsed, apps_created, apps_updated)
      provide insight for debugging and user feedback.
    - error_message stores the traceback or human-readable error on failure.
    """

    __tablename__ = "sync_logs"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sync_type: Mapped[SyncType] = mapped_column(
        SAEnum(SyncType, name="sync_type", values_callable=lambda x: [e.value for e in x], create_type=True),
        nullable=False,
    )
    status: Mapped[SyncStatus] = mapped_column(
        SAEnum(SyncStatus, name="sync_status", values_callable=lambda x: [e.value for e in x], create_type=True),
        nullable=False,
        default=SyncStatus.PENDING,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    emails_fetched: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    emails_parsed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    apps_created: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    apps_updated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="sync_logs", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<SyncLog id={self.id!s} type={self.sync_type} status={self.status}>"
        )
