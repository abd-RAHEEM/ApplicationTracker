"""UserSession model — tracks active refresh token sessions."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserSession(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Represents a user's authenticated session via a refresh token.

    Design decisions:
    - refresh_token_hash stores the bcrypt hash of the opaque token.
      The raw token is delivered via HttpOnly cookie and never stored.
    - is_revoked flag allows immediate invalidation without deleting the record
      (audit trail preserved).
    - ip_address and user_agent provide forensic context for suspicious activity.
    - One session per login — concurrent logins on multiple devices are supported
      because each login creates a separate UserSession row.
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash of the opaque refresh token",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="sessions", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<UserSession id={self.id!s} user_id={self.user_id!s} "
            f"revoked={self.is_revoked}>"
        )
