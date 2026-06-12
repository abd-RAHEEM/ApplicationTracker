"""ApplicationAnalytics — precomputed analytics per user (Q7 decision)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin, JSONB

if TYPE_CHECKING:
    from app.models.user import User


class ApplicationAnalytics(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Precomputed analytics snapshot for a user.

    Design decisions (Q7):
    - One row per user (UNIQUE on user_id). Updated in-place after every sync.
    - Storing in DB (not only Redis) ensures analytics survive Redis restarts.
    - Redis caching can be layered on top for sub-millisecond reads.
    - computed_at tracks freshness so the frontend can show "Last updated X ago".
    - monthly_data stores a JSON array: [{"month": "2026-01", "count": 12}, ...]
      Using JSONB allows direct indexing into the JSON in PostgreSQL if needed.
    - Rate columns (interview_rate, offer_rate) are Float (0.0–100.0 as %).
    """

    __tablename__ = "application_analytics"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_analytics_user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Status Counts ──────────────────────────────────────────────────────────
    total_applications: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    applied_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    assessment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    interview_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    offer_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    rejected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pending_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # ── Rate Metrics (%) ───────────────────────────────────────────────────────
    interview_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="(interview_count / applied_count) * 100",
    )
    offer_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="(offer_count / applied_count) * 100",
    )
    rejection_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="(rejected_count / applied_count) * 100",
    )
    response_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="((interview_count + offer_count + rejected_count) / total_applications) * 100",
    )

    # ── Time-Series Data ───────────────────────────────────────────────────────
    monthly_data: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='[{"month": "2026-01", "count": 12}, ...]',
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="analytics", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationAnalytics user_id={self.user_id!s} "
            f"total={self.total_applications} computed={self.computed_at!s}>"
        )
