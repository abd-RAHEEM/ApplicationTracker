"""Application model — core job application tracking record."""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.deleted_application import DeletedApplication
    from app.models.email import Email
    from app.models.status_history import ApplicationStatusHistory
    from app.models.user import User


class ApplicationStatus(str, enum.Enum):
    """
    Ordered status progression for a job application.

    Using str mixin allows direct JSON serialization without extra conversion.
    The CHECK constraint in the DB enforces valid values at the storage layer.
    """

    APPLIED = "applied"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    PENDING = "pending"


class StatusSource(str, enum.Enum):
    """Tracks how a status change originated."""

    EMAIL_IMPORT = "email_import"
    MANUAL_UPDATE = "manual_update"


class Application(Base, PrimaryKeyMixin, TimestampMixin):
    """
    A single job application identified from the user's Gmail.

    Design decisions:
    - current_status is denormalized here for fast dashboard aggregation.
      The full history is in ApplicationStatusHistory.
    - source_email_id links back to the triggering email (Gmail message ID)
      for the initial detection.
    - is_deleted / deleted_at implement soft-delete. The separate
      DeletedApplication row represents the Bin entry.
    - applied_at is inferred from the earliest email in the thread, not the
      system's created_at, for accurate timeline representation.
    - Composite indexes on (user_id, current_status) and (user_id, is_deleted)
      power the dashboard summary cards and table filters efficiently.
    """

    __tablename__ = "applications"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    current_status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, name="application_status", create_type=True),
        nullable=False,
        default=ApplicationStatus.APPLIED,
        index=True,
    )
    source_email_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Gmail message ID that first detected this application",
    )
    gmail_thread_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Gmail thread ID used for deduplication",
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Inferred from the earliest email in the thread",
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp of the most recent status change",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confidence_scores: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Confidence scores for entity extraction"
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="applications", lazy="noload")
    status_history: Mapped[list[ApplicationStatusHistory]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="noload",
        order_by="ApplicationStatusHistory.detected_at.asc()",
    )
    emails: Mapped[list[Email]] = relationship(
        "Email",
        back_populates="application",
        lazy="noload",
    )
    bin_record: Mapped[DeletedApplication | None] = relationship(
        "DeletedApplication",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id!s} company={self.company_name!r} "
            f"role={self.role_title!r} status={self.current_status}>"
        )
