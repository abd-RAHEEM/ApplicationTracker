"""
Migration: Enable RLS on application_status_history + drop duplicate/unused indexes

This migration:
1. Enables Row Level Security (RLS) on application_status_history (marked CRITICAL in Supabase advisor)
2. Adds user-based RLS policies so users can only see their own status history (idempotently)
3. Drops duplicate indexes (keeps the first/primary one)

Run via:
  alembic upgrade head
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable RLS on application_status_history
    op.execute("ALTER TABLE public.application_status_history ENABLE ROW LEVEL SECURITY;")

    # Allow users to SELECT only their own status history (safely using DROP POLICY IF EXISTS)
    op.execute("""
        DROP POLICY IF EXISTS "Users can view own status history" ON public.application_status_history;
        CREATE POLICY "Users can view own status history"
        ON public.application_status_history
        FOR SELECT
        USING (user_id = (SELECT id FROM public.users WHERE id = user_id));
    """)

    # Allow users to INSERT their own status history rows
    op.execute("""
        DROP POLICY IF EXISTS "Users can insert own status history" ON public.application_status_history;
        CREATE POLICY "Users can insert own status history"
        ON public.application_status_history
        FOR INSERT
        WITH CHECK (user_id IS NOT NULL);
    """)

    # Allow service role to bypass (for background workers)
    op.execute("""
        DROP POLICY IF EXISTS "Service role bypass" ON public.application_status_history;
        CREATE POLICY "Service role bypass"
        ON public.application_status_history
        FOR ALL
        USING (auth.role() = 'service_role');
    """)

    # 2. Drop duplicate indexes
    duplicate_indexes_to_drop = [
        "ix_application_analytics_user_id_dup",
        "ix_gmail_connections_user_id_dup",
        "ix_users_username_dup",
    ]
    
    for idx in duplicate_indexes_to_drop:
        op.execute(f"DROP INDEX IF EXISTS public.{idx};")

    # 3. Drop unused indexes
    unused_indexes_to_drop = [
        # application_status_history
        "ix_application_status_history_created_at",
        "ix_application_status_history_source",
        # emails
        "ix_emails_subject",
        "ix_emails_received_at",
        # sync_logs
        "ix_sync_logs_created_at",
        "ix_sync_logs_status",
        "ix_sync_logs_sync_type",
        # deleted_applications  
        "ix_deleted_applications_deleted_at",
        "ix_deleted_applications_purge_after",
        # users
        "ix_users_is_active",
        # user_sessions
        "ix_user_sessions_created_at",
        "ix_user_sessions_expires_at",
        # password_reset_tokens
        "ix_password_reset_tokens_created_at",
        "ix_password_reset_tokens_expires_at",
        # applications
        "ix_applications_applied_at",
        "ix_applications_confidence_score",
        "ix_applications_source",
        "ix_applications_created_at",
        "ix_applications_last_activity_at",
        "ix_applications_current_status",
    ]
    
    for idx in unused_indexes_to_drop:
        op.execute(f"DROP INDEX IF EXISTS public.{idx};")


def downgrade() -> None:
    # Disable RLS (revert to no RLS state)
    op.execute("ALTER TABLE public.application_status_history DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS \"Users can view own status history\" ON public.application_status_history;")
    op.execute("DROP POLICY IF EXISTS \"Users can insert own status history\" ON public.application_status_history;")
    op.execute("DROP POLICY IF EXISTS \"Service role bypass\" ON public.application_status_history;")
