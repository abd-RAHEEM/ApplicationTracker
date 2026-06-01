"""GmailConnection model — stores per-user Gmail OAuth tokens.

CHANGE LOG (Phase 1 final review):
  - Removed encrypted_access_token column entirely.
    Reasoning: Gmail access tokens are short-lived (~1 hour). They can always
    be regenerated from the refresh token on demand. Storing them adds zero
    architectural value while increasing the encrypted payload on disk and
    widening the blast radius if the encryption key is compromised.
    The Gmail service (Phase 2) will: decrypt the refresh token → call Google
    Token Endpoint → receive a fresh access token → use it immediately in memory.
    The token_expiry column is kept to enable proactive pre-refresh before expiry.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class GmailConnection(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Stores a user's Gmail OAuth 2.0 credentials.

    Design decisions:
    - UNIQUE constraint on user_id enforces one Gmail per user (as specified).
    - Only the refresh_token is persisted (encrypted with AES-256-GCM).
      Access tokens are generated on demand from the refresh token and used
      in-process only — never written to the database.
    - token_expiry is retained so the Gmail service can proactively refresh
      before the current access token expires, avoiding an unnecessary extra
      round-trip to Google on every sync.
    - last_successful_sync_at is the pivot for incremental sync. It is only
      updated AFTER a sync completes successfully. If a sync fails midway, the
      timestamp is NOT updated so the next sync safely re-processes from the
      same point (deduplication via emails.uq_email_user prevents double inserts).
    - initial_import_done separates first-time onboarding from ongoing sync.
    - disconnected_at records when the user voluntarily disconnected Gmail,
      allowing history to be preserved (per Q4 decision).
    - gmail_onboarding_completed tracks whether the user has completed the full
      Gmail onboarding flow (connect + initial import). Platform features are
      gated on this flag.
    """

    __tablename__ = "gmail_connections"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,                   # One Gmail account per user
        index=True,
    )
    gmail_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Verified Gmail address (used for password reset emails)",
    )
    # NOTE: encrypted_access_token has been removed.
    # Access tokens are generated on demand from encrypted_refresh_token.
    encrypted_refresh_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AES-256-GCM encrypted Gmail refresh token",
    )
    token_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC expiry time for the last-issued access token — used for proactive refresh",
    )
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
        comment="OAuth scopes granted (should only contain gmail.readonly)",
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp of successful OAuth connection",
    )
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Pivot for incremental sync — only updated on full success",
    )
    initial_import_done: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="True after the first historical import is completed",
    )
    initial_import_range: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User-selected historical import range string (e.g. 6_months)",
    )
    initial_import_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Calculated historical import start date",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="gmail_connection", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<GmailConnection user_id={self.user_id!s} "
            f"email={self.gmail_email!r}>"
        )
