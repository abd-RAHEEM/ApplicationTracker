"""Add is_onboarding_completed to users table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-01

is_onboarding_completed lifecycle:
  - False on registration (default).
  - False after Gmail OAuth callback (email verified, but import not configured yet).
  - True after user completes import configuration (POST /v1/gmail/onboarding/complete).

This separates "email verified" from "platform fully onboarded":
  is_email_verified=True  → Gmail OAuth done, can receive password reset emails.
  is_onboarding_completed=True → Import configured, all platform features unlocked.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment=(
                "True after the user completes import configuration. "
                "Gates all platform features (dashboard, analytics, applications)."
            ),
        ),
    )
    # Partial index: fast lookup of users who still need onboarding
    op.create_index(
        "idx_users_onboarding_incomplete",
        "users",
        ["id"],
        postgresql_where=sa.text("is_onboarding_completed = false AND is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("idx_users_onboarding_incomplete", table_name="users")
    op.drop_column("users", "is_onboarding_completed")
