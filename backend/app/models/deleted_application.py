"""DeletedApplication — Bin entry linking a soft-deleted application."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class DeletedApplication(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Represents a soft-deleted application in the Bin.

    Design decisions:
    - Separate table (not just a flag on applications) keeps the main
      applications table lean for dashboard queries.
    - UNIQUE constraint on application_id ensures one Bin entry per app —
      prevents duplicate Bin entries if bulk-delete is called twice.
    - purge_after = deleted_at + 15 days is computed at insert time.
      The Celery Beat cleanup job uses this column with a partial index
      WHERE is_purged = FALSE for efficient batch purging.
    - deleted_by distinguishes individual vs bulk delete actions for analytics.
    - restored_at / is_purged are the terminal states for a Bin record.
    """

    __tablename__ = "deleted_applications"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_deleted_application_id"),
    )

    application_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    purge_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="deleted_at + 15 days — set at insert time",
    )
    deleted_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user",
        comment="user | bulk_action",
    )
    restored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_purged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    application: Mapped[Application] = relationship(
        "Application", back_populates="bin_record", lazy="noload"
    )
    user: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<DeletedApplication app_id={self.application_id!s} "
            f"purge_after={self.purge_after!s}>"
        )
