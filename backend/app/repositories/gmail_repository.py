"""
Gmail connection repository.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gmail_connection import GmailConnection
from app.repositories.base_repository import BaseRepository


class GmailRepository(BaseRepository[GmailConnection]):
    """Data access layer for Gmail connections. One connection per user, permanent."""

    def __init__(self) -> None:
        super().__init__(GmailConnection)

    async def get_connection(
        self, session: AsyncSession, user_id: UUID
    ) -> GmailConnection | None:
        """Fetch the user's permanent Gmail connection."""
        result = await session.execute(
            select(GmailConnection).where(GmailConnection.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_connection(
        self,
        session: AsyncSession,
        user_id: UUID,
        gmail_email: str,
        encrypted_refresh_token: str,
        token_expiry: datetime,
        scopes: list[str],
    ) -> GmailConnection:
        """
        Create a permanent Gmail connection.
        This should only happen once per user during onboarding.
        """
        now = datetime.now(timezone.utc)
        return await self.create(
            session,
            user_id=user_id,
            gmail_email=gmail_email,
            encrypted_refresh_token=encrypted_refresh_token,
            token_expiry=token_expiry,
            scopes=scopes,
            connected_at=now,
        )

    async def complete_initial_import_config(
        self, session: AsyncSession, user_id: UUID, import_range: str, import_from: datetime
    ) -> GmailConnection | None:
        """
        Mark the initial import configuration as done and store the range/date.
        """
        result = await session.execute(
            update(GmailConnection)
            .where(GmailConnection.user_id == user_id)
            .values(
                initial_import_done=True,
                initial_import_range=import_range,
                initial_import_from=import_from,
            )
            .returning(GmailConnection)
        )
        updated = result.scalar_one_or_none()
        await session.flush()
        return updated

    async def update_sync_timestamp(
        self, session: AsyncSession, user_id: UUID, sync_time: datetime
    ) -> None:
        """Update the last_successful_sync_at timestamp."""
        await session.execute(
            update(GmailConnection)
            .where(GmailConnection.user_id == user_id)
            .values(last_successful_sync_at=sync_time)
        )
        await session.flush()


gmail_repository = GmailRepository()
