"""
Refresh token rotation test stubs.

Testing strategy:
  - Valid refresh: old session revoked, new session created, new cookies set.
  - Replay attack: reusing a refresh token after it was rotated → all sessions
    for the user are revoked (scorched-earth defence), 401 returned.
  - Expired refresh token: session with expires_at < now() → 401.
  - Revoked session: session with is_revoked=True → 401.
  - Tampered cookie: garbage value in refresh_token cookie → 401.
  - Inactive user: user deactivated between refresh calls → 401.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestRefreshTokenRotation:
    """POST /v1/auth/refresh"""

    async def test_refresh_issues_new_tokens(
        self, authenticated_client: AsyncClient, session: AsyncSession
    ):
        """Calling /refresh rotates both tokens and sets new cookies."""
        raise NotImplementedError

    async def test_refresh_revokes_old_session(
        self, authenticated_client: AsyncClient, session: AsyncSession
    ):
        """After refresh, the old session record has is_revoked=True."""
        raise NotImplementedError

    async def test_refresh_replay_revokes_all_sessions(
        self, authenticated_client: AsyncClient, session: AsyncSession
    ):
        """
        Using a refresh token AFTER it has been rotated:
          1. First /refresh succeeds — old session revoked, new session created.
          2. Second /refresh with the old token → hash mismatch.
          3. Backend detects replay — revokes ALL sessions for the user.
          4. Returns 401 INVALID_TOKEN.
        """
        raise NotImplementedError

    async def test_refresh_expired_session_returns_401(
        self, session: AsyncSession
    ):
        """Session with expires_at in the past returns 401 SESSION_REVOKED."""
        raise NotImplementedError

    async def test_refresh_revoked_session_returns_401(
        self, session: AsyncSession
    ):
        """Session with is_revoked=True returns 401 SESSION_REVOKED."""
        raise NotImplementedError

    async def test_refresh_missing_cookie_returns_401(
        self, client: AsyncClient
    ):
        """Request with no refresh_token cookie returns 401 UNAUTHORIZED."""
        raise NotImplementedError

    async def test_refresh_inactive_user_returns_401(
        self, session: AsyncSession
    ):
        """User deactivated between login and refresh → 401."""
        raise NotImplementedError
