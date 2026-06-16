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
    bind = op.get_bind()
    
    # 1. Update test_user_875412 in users table
    bind.execute(sa.text("""
        UPDATE users 
        SET is_onboarding_completed = true, is_email_verified = true 
        WHERE username = 'test_user_875412'
    """))
    
    # 2. Get user's ID
    result = bind.execute(sa.text("SELECT id FROM users WHERE username = 'test_user_875412'"))
    row = result.fetchone()
    if row:
        user_id = row[0]
        # Insert or update gmail_connections
        bind.execute(sa.text(f"""
            INSERT INTO gmail_connections (
                id, user_id, gmail_email, encrypted_refresh_token, 
                connected_at, initial_import_done, initial_import_range, 
                initial_import_from, scopes, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), '{user_id}', 'test_user_875412@gmail.com', 'mocked_refresh_token_not_real',
                now(), true, '6_months', now(), ARRAY['https://www.googleapis.com/auth/gmail.readonly'], now(), now()
            )
            ON CONFLICT (user_id) DO UPDATE 
            SET initial_import_done = true, gmail_email = 'test_user_875412@gmail.com'
        """))


def downgrade() -> None:
    pass
