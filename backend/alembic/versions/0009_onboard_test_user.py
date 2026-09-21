"""Onboard test user in DB.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-16
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Originally inserted a test user with fake Gmail credentials.
    # This poisoned fresh databases (mocked token → decrypt crash,
    # initial_import_done=True → no historical fetch). Neutralized.
    pass


def downgrade() -> None:
    pass
