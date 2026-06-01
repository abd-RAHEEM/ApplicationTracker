"""
Authorization test stubs — route protection and user isolation.

Testing strategy:
  - Protected routes return 401 with no token cookie.
  - Protected routes return 401 with an expired access token (before refresh).
  - Protected routes return 403 when accessing another user's resource.
  - All application/email/analytics queries must be filtered by user_id —
    verified by attempting cross-user access and asserting 404 (not 403,
    to avoid leaking resource existence).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestRouteProtection:
    """General authentication guard on all /v1/* routes."""

    async def test_protected_route_without_token_returns_401(
        self, client: AsyncClient
    ):
        """GET /v1/users/me without cookie → 401 UNAUTHORIZED."""
        raise NotImplementedError

    async def test_protected_route_with_expired_token_returns_401(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Expired access_token cookie → 401 (client should call /refresh first)."""
        raise NotImplementedError

    async def test_protected_route_with_tampered_token_returns_401(
        self, client: AsyncClient
    ):
        """Forged JWT signature → 401 INVALID_TOKEN."""
        raise NotImplementedError

    async def test_inactive_user_returns_401(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Token valid but user.is_active=False → 401 UNAUTHORIZED."""
        raise NotImplementedError


class TestUserIsolation:
    """Cross-user data isolation — all queries must be scoped by user_id."""

    async def test_cannot_read_another_users_application(
        self, client: AsyncClient, session: AsyncSession
    ):
        """
        User A requests application owned by User B → 404 NOT_FOUND.
        Must return 404, not 403, to avoid leaking resource existence.
        """
        raise NotImplementedError

    async def test_cannot_update_another_users_application(
        self, client: AsyncClient, session: AsyncSession
    ):
        """PATCH /v1/applications/{id} for another user's app → 404."""
        raise NotImplementedError

    async def test_cannot_delete_another_users_application(
        self, client: AsyncClient, session: AsyncSession
    ):
        """DELETE /v1/applications/{id} for another user's app → 404."""
        raise NotImplementedError

    async def test_cannot_read_another_users_analytics(
        self, client: AsyncClient, session: AsyncSession
    ):
        """GET /v1/analytics for a different user is impossible — always scoped."""
        raise NotImplementedError
