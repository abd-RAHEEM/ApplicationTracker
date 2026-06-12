"""Add response_rate to application_analytics.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-12
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "application_analytics",
        sa.Column(
            "response_rate",
            sa.Float(),
            nullable=True,
            comment="((interview_count + offer_count + rejected_count) / total_applications) * 100",
        ),
    )


def downgrade() -> None:
    op.drop_column("application_analytics", "response_rate")
