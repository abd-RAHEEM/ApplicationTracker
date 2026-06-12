"""ApplicationStatusHistory — immutable audit log of status changes."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.application import ApplicationStatus, StatusSource
from app.models.base import Base, PrimaryKeyMixin, TimestampMixin, JSONB

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class ApplicationStatusHistory(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Immutable log of every status change for an application.

    Design decisions:
    - Records are NEVER updated — only appended. This preserves the full
      transition trail (Applied → Interview → Offer, etc.).
    - detected_at is the timestamp of the email that triggered the change,
      not the system's created_at, so the timeline is accurate.
    - source distinguishes email-driven changes ('email_import') from
      user-initiated changes ('manual_update') — required by Q5.
    - user_id is denormalized here for simpler user-scoped queries without
      a JOIN through applications.
    """

    __tablename__ = "application_status_history"

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
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="The new status after this transition",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=StatusSource.EMAIL_IMPORT.value,
        comment="email_import | manual_update",
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp of the email that triggered this status change",
    )
    source_email_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Gmail message ID that caused this status transition (null for manual)",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional user note for manual status updates",
    )
    confidence_scores: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Confidence scores for this classification"
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    application: Mapped[Application] = relationship(
        "Application", back_populates="status_history", lazy="noload"
    )
    user: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<StatusHistory app_id={self.application_id!s} "
            f"status={self.status!r} source={self.source!r}>"
        )
