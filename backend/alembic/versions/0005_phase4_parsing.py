"""Phase 4 parsing and confidence tracking schema changes.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-01

Changes:
  - Add `is_parsed`, `parsed_at`, `parse_attempts`, `last_parse_error` to emails
  - Add `confidence_scores` (JSONB) to applications
  - Add `confidence_scores` (JSONB) to application_status_history
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── emails table updates ─────────────────────────────────────────────────
    op.add_column("emails", sa.Column("is_parsed", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("emails", sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("emails", sa.Column("parse_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("emails", sa.Column("last_parse_error", sa.Text(), nullable=True))

    # ── applications table updates ───────────────────────────────────────────
    op.add_column("applications", sa.Column("confidence_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # ── application_status_history updates ────────────────────────────────────
    op.add_column("application_status_history", sa.Column("confidence_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # ── application_status_history updates ────────────────────────────────────
    op.drop_column("application_status_history", "confidence_scores")

    # ── applications table updates ───────────────────────────────────────────
    op.drop_column("applications", "confidence_scores")

    # ── emails table updates ─────────────────────────────────────────────────
    op.drop_column("emails", "last_parse_error")
    op.drop_column("emails", "parse_attempts")
    op.drop_column("emails", "parsed_at")
    op.drop_column("emails", "is_parsed")
