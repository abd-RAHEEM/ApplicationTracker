"""Phase 3 Email Sync schema modifications.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-01

Changes:
  - Rename emails columns to match Phase 3 constraints
  - Add recipient and date to emails
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── emails table updates ─────────────────────────────────────────────────
    # Drop old constraints and indexes
    op.drop_constraint("uq_email_user_gmail_id", "emails", type_="unique")
    op.drop_index("idx_emails_received_at", table_name="emails")
    
    # Rename columns
    op.alter_column("emails", "gmail_message_id", new_column_name="gmail_msg_id")
    op.alter_column("emails", "raw_labels", new_column_name="gmail_label_ids")
    op.alter_column("emails", "received_at", new_column_name="gmail_internal_date")
    
    # Add new columns
    op.add_column("emails", sa.Column("recipient", sa.Text(), nullable=True))
    op.add_column("emails", sa.Column("date", sa.DateTime(timezone=True), nullable=True))
    
    # Recreate constraints and indexes
    op.create_unique_constraint("uq_emails_user_msg", "emails", ["user_id", "gmail_msg_id"])
    op.create_index("idx_emails_internal_date", "emails", ["user_id", "gmail_internal_date"])


def downgrade() -> None:
    # Drop constraints and indexes
    op.drop_constraint("uq_emails_user_msg", "emails", type_="unique")
    op.drop_index("idx_emails_internal_date", table_name="emails")
    
    # Drop new columns
    op.drop_column("emails", "date")
    op.drop_column("emails", "recipient")
    
    # Rename columns back
    op.alter_column("emails", "gmail_internal_date", new_column_name="received_at")
    op.alter_column("emails", "gmail_label_ids", new_column_name="raw_labels")
    op.alter_column("emails", "gmail_msg_id", new_column_name="gmail_message_id")
    
    # Recreate old constraints and indexes
    op.create_unique_constraint("uq_email_user_gmail_id", "emails", ["user_id", "gmail_message_id"])
    op.create_index("idx_emails_received_at", "emails", ["user_id", "received_at"])
