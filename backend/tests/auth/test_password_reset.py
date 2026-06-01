"""
Password reset flow test stubs.

Testing strategy:

Forgot password (POST /v1/auth/forgot-password):
  - Always returns 200 with identical message (anti-enumeration).
  - Non-existent username → 200 (no email sent).
  - Existing user, is_email_verified=False → 200 (no email sent).
  - Existing verified user → email sent, token stored in DB.
  - Token stored as SHA-256 hash (NOT plaintext).
  - Multiple reset requests: only the latest token is valid.

Reset password (POST /v1/auth/reset-password):
  - Valid token + new password → password updated, sessions revoked, token marked used.
  - Expired token → 401 INVALID_TOKEN.
  - Already-used token → 401 INVALID_TOKEN.
  - Non-existent token → 401 INVALID_TOKEN.
  - Weak new password → 422 VALIDATION_ERROR.
  - After successful reset: old sessions cannot refresh.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestForgotPassword:
    """POST /v1/auth/forgot-password"""

    async def test_forgot_password_always_returns_200(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Identical 200 response for existing user, non-existent, and unverified."""
        raise NotImplementedError

    async def test_forgot_password_unverified_user_no_email_sent(
        self, client: AsyncClient, test_user, session: AsyncSession
    ):
        """User with is_email_verified=False: no token created, no email sent."""
        raise NotImplementedError

    async def test_forgot_password_verified_user_creates_token(
        self, client: AsyncClient, verified_user, session: AsyncSession
    ):
        """Verified user: token_hash stored in password_reset_tokens, email sent."""
        raise NotImplementedError

    async def test_forgot_password_token_stored_as_hash(
        self, client: AsyncClient, verified_user, session: AsyncSession
    ):
        """The raw token is NEVER in the DB — only its SHA-256 hash."""
        raise NotImplementedError

    async def test_forgot_password_rate_limited(
        self, client: AsyncClient, session: AsyncSession
    ):
        """More than N requests in T seconds returns 429."""
        raise NotImplementedError


class TestResetPassword:
    """POST /v1/auth/reset-password"""

    async def test_reset_success_updates_password(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Valid token → password hash updated, login with new password succeeds."""
        raise NotImplementedError

    async def test_reset_success_revokes_all_sessions(
        self, client: AsyncClient, session: AsyncSession
    ):
        """After reset, existing sessions have is_revoked=True."""
        raise NotImplementedError

    async def test_reset_success_marks_token_used(
        self, client: AsyncClient, session: AsyncSession
    ):
        """After reset, the reset token has is_used=True."""
        raise NotImplementedError

    async def test_reset_with_used_token_returns_401(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Reusing a reset token returns 401 INVALID_TOKEN."""
        raise NotImplementedError

    async def test_reset_with_expired_token_returns_401(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Token past its expires_at returns 401 INVALID_TOKEN."""
        raise NotImplementedError

    async def test_reset_weak_password_returns_422(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Weak new password rejected at schema layer, token NOT consumed."""
        raise NotImplementedError
