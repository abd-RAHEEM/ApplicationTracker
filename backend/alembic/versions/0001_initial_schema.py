"""Initial database schema — all tables created in FK dependency order.

Revision ID: 0001
Revises:
Create Date: 2026-06-01

CHANGE LOG (Phase 1 final review — applied before any migrations run):
  - gmail_connections: removed encrypted_access_token column.
    Access tokens are generated on demand from encrypted_refresh_token.
  - users: added is_email_verified column (set during Gmail OAuth completion).
  - Removed notifications table entirely (UI-only SSE+toast events).
  - Removed notification_type ENUM entirely.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUMS ───────────────────────────────────────────────────────────────────
    application_status = postgresql.ENUM(
        "applied", "assessment", "interview", "offer", "rejected", "pending",
        name="application_status",
        create_type=False,
    )
    application_status.create(op.get_bind(), checkfirst=True)

    sync_type = postgresql.ENUM(
        "initial_import", "incremental", "manual",
        name="sync_type",
        create_type=False,
    )
    sync_type.create(op.get_bind(), checkfirst=True)

    sync_status = postgresql.ENUM(
        "pending", "running", "completed", "failed",
        name="sync_status",
        create_type=False,
    )
    sync_status.create(op.get_bind(), checkfirst=True)

    # NOTE: notification_type ENUM intentionally omitted — no notifications table.

    # ── users ───────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # is_email_verified: set True when Gmail OAuth completes (Google provides
        # a verified address). Gating password reset on this prevents sending
        # emails to unverified / untrusted addresses.
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("idx_users_username", "users", ["username"], unique=True)
    op.create_index("idx_users_created_at", "users", ["created_at"])

    # ── user_sessions ────────────────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("idx_sessions_expires_at", "user_sessions", ["expires_at"])

    # ── password_reset_tokens ─────────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_reset_token_hash"),
    )
    op.create_index("idx_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("idx_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])

    # ── gmail_connections ─────────────────────────────────────────────────────
    # NOTE: encrypted_access_token column intentionally omitted.
    # Access tokens are generated on demand from encrypted_refresh_token.
    op.create_table(
        "gmail_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gmail_email", sa.String(255), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False,
                  server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("initial_import_done", sa.Boolean(), nullable=False,
                  server_default="false"),
        sa.Column("initial_import_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_gmail_connections_user_id"),
    )
    op.create_index("idx_gmail_user_id", "gmail_connections", ["user_id"], unique=True)
    op.create_index(
        "idx_gmail_active",
        "gmail_connections",
        ["user_id"],
        postgresql_where=sa.text("is_active = true"),
    )

    # ── applications ─────────────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("role_title", sa.String(255), nullable=False),
        sa.Column("current_status", sa.Enum("applied", "assessment", "interview",
                                            "offer", "rejected", "pending",
                                            name="application_status"), nullable=False,
                  server_default="applied"),
        sa.Column("source_email_id", sa.String(255), nullable=True),
        sa.Column("gmail_thread_id", sa.String(255), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_apps_user_id", "applications", ["user_id"])
    op.create_index("idx_apps_user_status", "applications", ["user_id", "current_status"])
    op.create_index("idx_apps_user_deleted", "applications", ["user_id", "is_deleted"])
    op.create_index("idx_apps_last_activity", "applications",
                    ["user_id", "last_activity_at"])
    op.create_index("idx_apps_thread_id", "applications", ["gmail_thread_id"])

    # ── application_status_history ────────────────────────────────────────────
    op.create_table(
        "application_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False,
                  server_default="email_import"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_email_id", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_history_app_id", "application_status_history", ["application_id"])
    op.create_index("idx_history_user_id", "application_status_history", ["user_id"])
    op.create_index("idx_history_detected_at", "application_status_history",
                    ["application_id", "detected_at"])

    # ── emails ────────────────────────────────────────────────────────────────
    op.create_table(
        "emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("gmail_message_id", sa.String(255), nullable=False),
        sa.Column("gmail_thread_id", sa.String(255), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("sender", sa.String(500), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("raw_labels", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("is_processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"],
                                ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "gmail_message_id",
                            name="uq_email_user_gmail_id"),
    )
    op.create_index("idx_emails_user_id", "emails", ["user_id"])
    op.create_index("idx_emails_app_id", "emails", ["application_id"])
    op.create_index("idx_emails_thread_id", "emails", ["gmail_thread_id"])
    op.create_index("idx_emails_received_at", "emails", ["user_id", "received_at"])
    op.create_index(
        "idx_emails_unprocessed",
        "emails",
        ["user_id", "is_processed"],
        postgresql_where=sa.text("is_processed = false"),
    )

    # ── sync_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sync_type", sa.Enum("initial_import", "incremental", "manual",
                                       name="sync_type"), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed",
                                    name="sync_status"), nullable=False,
                  server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emails_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("emails_parsed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("apps_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("apps_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_sync_user_id", "sync_logs", ["user_id"])
    op.create_index("idx_sync_user_status", "sync_logs", ["user_id", "status"])
    op.create_index("idx_sync_started_at", "sync_logs", ["user_id", "started_at"])

    # ── deleted_applications ──────────────────────────────────────────────────
    op.create_table(
        "deleted_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_by", sa.String(50), nullable=False, server_default="user"),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_purged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("application_id", name="uq_deleted_application_id"),
    )
    op.create_index("idx_bin_user_id", "deleted_applications", ["user_id"])
    op.create_index(
        "idx_bin_purge_after",
        "deleted_applications",
        ["purge_after"],
        postgresql_where=sa.text("is_purged = false"),
    )

    # NOTE: notifications table intentionally omitted.
    # Notifications are UI-only events via SSE + frontend toasts.

    # ── application_analytics ─────────────────────────────────────────────────
    op.create_table(
        "application_analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("total_applications", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("applied_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assessment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interview_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interview_rate", sa.Float(), nullable=True),
        sa.Column("offer_rate", sa.Float(), nullable=True),
        sa.Column("rejection_rate", sa.Float(), nullable=True),
        sa.Column("monthly_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_analytics_user_id"),
    )
    op.create_index("idx_analytics_user_id", "application_analytics", ["user_id"],
                    unique=True)


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("application_analytics")
    op.drop_table("deleted_applications")
    op.drop_table("sync_logs")
    op.drop_table("emails")
    op.drop_table("application_status_history")
    op.drop_table("applications")
    op.drop_table("gmail_connections")
    op.drop_table("password_reset_tokens")
    op.drop_table("user_sessions")
    op.drop_table("users")

    # Drop enums (notification_type intentionally absent)
    for enum_name in ["sync_status", "sync_type", "application_status"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
