"""Architecture pivot: permanent one-user-one-gmail model.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-01

Changes:
  - Drop `is_active` (connections are permanent)
  - Drop `disconnected_at` (cannot disconnect)
  - Add `initial_import_range` (String, nullable)
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add initial_import_range
    op.add_column(
        "gmail_connections",
        sa.Column(
            "initial_import_range",
            sa.String(255),
            nullable=True,
            comment="The selected time range for historical import (e.g. 6_months)",
        ),
    )
    # Drop columns related to deactivation
    op.drop_column("gmail_connections", "is_active")
    op.drop_column("gmail_connections", "disconnected_at")


def downgrade() -> None:
    # Re-add columns
    op.add_column(
        "gmail_connections",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
    )
    op.add_column(
        "gmail_connections",
        sa.Column(
            "disconnected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Drop new column
    op.drop_column("gmail_connections", "initial_import_range")
