"""PasswordResetToken — single-use, time-limited password reset tokens."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PasswordResetToken(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Single-use password reset token.

    Design decisions:
    - token_hash stores SHA-256(raw_token). The raw token is sent to the user
      via email and never stored. SHA-256 (not bcrypt) is used because reset
      tokens are high-entropy random strings — bcrypt's slowness is unnecessary
      and would add latency to the reset flow.
    - is_used flag prevents replay attacks. Once used, the token is permanently
      invalidated even if expires_at has not passed.
    - expires_at is set to now() + 15 minutes (configured via settings).
    - Multiple outstanding reset tokens are allowed (user requests reset twice);
      the auth service validates is_used=False AND expires_at > now().
    """

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="SHA-256 hex digest of the raw reset token",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="password_reset_tokens", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<PasswordResetToken user_id={self.user_id!s} "
            f"used={self.is_used} expires={self.expires_at!s}>"
        )
