"""
Authentication test stubs — register and login flows.

Testing strategy:
  - Happy path: valid credentials succeed.
  - Duplicate username: 409 Conflict raised.
  - Wrong password: 401 Unauthorized with same message as wrong username.
  - Inactive user: 401 Unauthorized (same as wrong password — no enumeration).
  - Password strength: rejected at schema validation layer (422).
  - Cookies: verify access_token and refresh_token cookies are set.
  - Login response: verify gmail_connected and initial_import_done fields.

NOT tested here (tested in dedicated modules):
  - Token refresh rotation
  - Password reset flow
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestRegister:
    """POST /v1/auth/register"""

    async def test_register_success(self, client: AsyncClient, session: AsyncSession):
        """Valid payload creates user, returns 201, no auto-login."""
        raise NotImplementedError("Implement in Phase 1 test run")

    async def test_register_duplicate_username_returns_409(
        self, client: AsyncClient, test_user, session: AsyncSession
    ):
        """Registering with an existing username returns 409 CONFLICT."""
        raise NotImplementedError

    async def test_register_weak_password_returns_422(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Password without uppercase/digit/special char returns 422."""
        raise NotImplementedError

    async def test_register_password_mismatch_returns_422(
        self, client: AsyncClient, session: AsyncSession
    ):
        """confirm_password != password returns 422."""
        raise NotImplementedError

    async def test_register_invalid_username_chars_returns_422(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Username with spaces or special chars returns 422."""
        raise NotImplementedError


class TestLogin:
    """POST /v1/auth/login"""

    async def test_login_success_sets_cookies(
        self, client: AsyncClient, test_user, session: AsyncSession
    ):
        """Valid credentials set HttpOnly access_token and refresh_token cookies."""
        raise NotImplementedError

    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, test_user, session: AsyncSession
    ):
        """Wrong password returns 401 INVALID_CREDENTIALS."""
        raise NotImplementedError

    async def test_login_wrong_username_returns_same_401(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Wrong username returns identical 401 as wrong password (anti-enumeration)."""
        raise NotImplementedError

    async def test_login_inactive_user_returns_401(
        self, client: AsyncClient, session: AsyncSession
    ):
        """Deactivated user returns 401 (same message, no information leak)."""
        raise NotImplementedError

    async def test_login_response_includes_gmail_status(
        self, client: AsyncClient, verified_user, session: AsyncSession
    ):
        """Login response body includes gmail_connected and initial_import_done."""
        raise NotImplementedError

    async def test_login_rate_limit(self, client: AsyncClient, session: AsyncSession):
        """More than N login attempts in T seconds returns 429."""
        raise NotImplementedError


class TestLogout:
    """POST /v1/auth/logout"""

    async def test_logout_revokes_session(
        self, client: AsyncClient, authenticated_client, session: AsyncSession
    ):
        """Logout marks session is_revoked=True and clears cookies."""
        raise NotImplementedError

    async def test_logout_without_token_returns_401(
        self, client: AsyncClient, session: AsyncSession
    ):
        raise NotImplementedError
