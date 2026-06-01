"""
Email model — stores synchronized email metadata and snippets.
NO FULL BODIES ALLOWED.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class Email(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Metadata record for a processed Gmail message.
    """

    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "gmail_msg_id",
            name="uq_emails_user_msg",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gmail_msg_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Globally unique Gmail message ID",
    )
    gmail_thread_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Gmail thread ID for grouping related emails",
    )
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="From header: 'Display Name <email@domain.com>'",
    )
    recipient: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="To header",
    )
    date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date header parsed as datetime",
    )
    gmail_internal_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    snippet: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="First ~200 chars of body — full body is never persisted",
    )
    gmail_label_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text),
        nullable=True,
        comment="Gmail system labels e.g. ['INBOX', 'UNREAD']",
    )
    is_parsed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    parse_attempts: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    last_parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", lazy="noload")
    application: Mapped[Application | None] = relationship(
        "Application", back_populates="emails", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<Email id={self.id!s} gmail_id={self.gmail_msg_id!r} "
            f"processed={self.is_processed}>"
        )
