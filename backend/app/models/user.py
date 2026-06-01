"""
User model — core identity record for every account.

CHANGE LOG (Phase 1 final review):
  - Added is_gmail_onboarded flag (replaces implied logic spread across
    gmail_connections.initial_import_done). Platform access is gated on this.
  - Added is_email_verified flag. Reasoning: see Item 6 of Phase 1 review.
    Gmail OAuth acts as the verification event — when a user successfully
    completes Gmail OAuth, we receive a verified Gmail address directly from
    Google, making it the strongest possible email verification signal.
    is_email_verified is set to True at the same time initial_import_done
    is set to True.
  - Removed 'notifications' relationship (notifications table removed per Item 2).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.application_analytics import ApplicationAnalytics
    from app.models.gmail_connection import GmailConnection
    from app.models.password_reset_token import PasswordResetToken
    from app.models.sync_log import SyncLog
    from app.models.user_session import UserSession


class User(Base, PrimaryKeyMixin, TimestampMixin):
    """
    Core user identity.

    Design decisions:
    - username is the login identifier (not email) per spec.
    - hashed_password stores bcrypt output only — plaintext is never persisted.
    - is_active allows account suspension without deletion (data integrity).
    - is_email_verified: set to True when Gmail OAuth is completed. Gmail OAuth
      provides a Google-verified email address, which is the strongest
      verification signal available without building a separate email flow.
      Required for password reset (cannot send to an unverified address).
    - is_gmail_onboarded: True when gmail_connection.initial_import_done is True.
      This is the platform access gate. All dashboard/app/analytics routes
      check this flag (via get_current_user dependency in Phase 2).
    - No email column: the user's Gmail email is captured in GmailConnection.
      Password reset uses the connected Gmail email address.
    """

    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique login handle — alphanumeric + underscore, 3–100 chars",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash — never store plaintext",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="False when account is soft-deleted or suspended",
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment=(
            "True after Gmail OAuth completes. Google provides a verified email "
            "address, which is used for password reset delivery. "
            "Users without verified email cannot request password reset."
        ),
    )
    is_onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment=(
            "True after the user completes import configuration. "
            "Gates all platform features: dashboard, applications, analytics, sync. "
            "Lifecycle: False on register → False after OAuth → True after import config."
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    sessions: Mapped[list[UserSession]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    gmail_connection: Mapped[GmailConnection | None] = relationship(
        "GmailConnection",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="noload",
    )
    applications: Mapped[list[Application]] = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    sync_logs: Mapped[list[SyncLog]] = relationship(
        "SyncLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    analytics: Mapped[ApplicationAnalytics | None] = relationship(
        "ApplicationAnalytics",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!s} username={self.username!r}>"
