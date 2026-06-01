"""
Models package — imports all ORM models so Alembic can discover them.

IMPORTANT: All models must be imported here so that:
  1. SQLAlchemy's metadata registry is populated at startup.
  2. Alembic's env.py can call `from app.models import *` and see all tables.

Import order follows foreign-key dependencies (parents before children).

CHANGE LOG (Phase 1 final review):
  - Removed Notification and NotificationType imports.
    Notifications are UI-only events delivered via SSE + frontend toasts.
    No DB table required.
"""
from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.user import User
from app.models.user_session import UserSession
from app.models.password_reset_token import PasswordResetToken
from app.models.gmail_connection import GmailConnection
from app.models.application import Application, ApplicationStatus, StatusSource
from app.models.status_history import ApplicationStatusHistory
from app.models.email import Email
from app.models.sync_log import SyncLog, SyncStatus, SyncType
from app.models.deleted_application import DeletedApplication
from app.models.application_analytics import ApplicationAnalytics

__all__ = [
    # Base
    "Base",
    "PrimaryKeyMixin",
    "TimestampMixin",
    # Users & Auth
    "User",
    "UserSession",
    "PasswordResetToken",
    # Gmail
    "GmailConnection",
    # Applications
    "Application",
    "ApplicationStatus",
    "StatusSource",
    "ApplicationStatusHistory",
    "Email",
    # Sync
    "SyncLog",
    "SyncStatus",
    "SyncType",
    # Bin
    "DeletedApplication",
    # Analytics
    "ApplicationAnalytics",
]
