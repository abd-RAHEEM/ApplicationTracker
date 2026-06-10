"""Migration: Harden RLS and policies

Revision ID: 0007
Revises: 0006
"""
from typing import Sequence, Union
import os
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Read the SQL file containing RLS hardening statements and execute it
    sql_path = os.path.join(os.path.dirname(__file__), "0007_rls_hardening.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_commands = f.read()
    
    # Execute SQL blocks
    op.execute(sql_commands)


def downgrade() -> None:
    # Revert to migration 0006 policies if downgraded
    # application_status_history
    op.execute("DROP POLICY IF EXISTS \"Users can view own status history\" ON public.application_status_history;")
    op.execute("DROP POLICY IF EXISTS \"Users can insert own status history\" ON public.application_status_history;")
    op.execute("DROP POLICY IF EXISTS \"Service role bypass\" ON public.application_status_history;")
    
    op.execute("""
        CREATE POLICY "Users can view own status history"
        ON public.application_status_history
        FOR SELECT
        USING (user_id = (SELECT id FROM public.users WHERE id = user_id));
        
        CREATE POLICY "Users can insert own status history"
        ON public.application_status_history
        FOR INSERT
        WITH CHECK (user_id IS NOT NULL);
        
        CREATE POLICY "Service role bypass"
        ON public.application_status_history
        FOR ALL
        USING (auth.role() = 'service_role');
    """)
