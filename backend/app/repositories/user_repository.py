"""User repository — data access for the users table."""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """Data access layer for User records."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_username(
        self, session: AsyncSession, username: str
    ) -> User | None:
        """
        Fetch a user by their unique username.

        Used for login, password reset, and uniqueness checks.
        Usernames are stored lowercase — compare accordingly.
        """
        result = await session.execute(
            select(User).where(User.username == username.lower())
        )
        return result.scalar_one_or_none()

    async def username_exists(self, session: AsyncSession, username: str) -> bool:
        """Check whether a username is already taken (case-insensitive)."""
        return await self.exists(session, username=username.lower())

    async def get_active_by_id(
        self, session: AsyncSession, user_id: UUID
    ) -> User | None:
        """
        Fetch an active user by ID.

        Returns None for soft-disabled (is_active=False) accounts.
        Used by the auth guard so suspended users cannot make API calls.
        """
        result = await session.execute(
            select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def deactivate(self, session: AsyncSession, user_id: UUID) -> bool:
        """
        Set is_active=False for a user (soft account deletion).

        Returns True if the user was found and deactivated, False if not found.
        """
        result = await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)
            .returning(User.id)
        )
        affected = result.scalar_one_or_none()
        await session.flush()
        return affected is not None

    async def update_password(
        self, session: AsyncSession, user_id: UUID, new_hashed_password: str
    ) -> bool:
        """Update hashed_password for a user. Returns True if found."""
        result = await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=new_hashed_password)
            .returning(User.id)
        )
        affected = result.scalar_one_or_none()
        await session.flush()
        logger.info("password_updated", user_id=str(user_id))
        return affected is not None

    async def mark_email_verified(self, session: AsyncSession, user_id: UUID) -> None:
        """Set is_email_verified to True (called after Gmail OAuth)."""
        await session.execute(
            update(User).where(User.id == user_id).values(is_email_verified=True)
        )
        await session.flush()

    async def mark_onboarding_completed(self, session: AsyncSession, user_id: UUID) -> None:
        """Set is_onboarding_completed to True (called after import config)."""
        await session.execute(
            update(User).where(User.id == user_id).values(is_onboarding_completed=True)
        )
        await session.flush()


# Singleton instance — injected via FastAPI Depends
user_repository = UserRepository()
