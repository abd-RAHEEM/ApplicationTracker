"""Sync Log repository."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_log import SyncLog, SyncStatus, SyncType
from app.repositories.base_repository import BaseRepository


class SyncLogRepository(BaseRepository[SyncLog]):
    """Data access layer for sync logs."""

    def __init__(self) -> None:
        super().__init__(SyncLog)

    async def start_sync(
        self, session: AsyncSession, user_id: UUID, sync_type: SyncType, task_id: str | None = None
    ) -> SyncLog:
        """Creates a new RUNNING sync log."""
        log = await self.create(
            session,
            user_id=user_id,
            sync_type=sync_type,
            status=SyncStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            celery_task_id=task_id,
        )
        return log

    async def finish_sync(
        self,
        session: AsyncSession,
        log_id: UUID,
        status: SyncStatus,
        emails_fetched: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Marks a sync as completed or failed with statistics."""
        await session.execute(
            update(SyncLog)
            .where(SyncLog.id == log_id)
            .values(
                status=status,
                completed_at=datetime.now(timezone.utc),
                emails_fetched=emails_fetched,
                error_message=error_message,
            )
        )
        await session.flush()

    async def increment_progress(
        self, session: AsyncSession, log_id: UUID, batch_fetched_count: int
    ) -> None:
        """Incrementally update progress without finishing the sync."""
        await session.execute(
            update(SyncLog)
            .where(SyncLog.id == log_id)
            .values(
                emails_fetched=SyncLog.emails_fetched + batch_fetched_count,
            )
        )
        await session.flush()


sync_log_repository = SyncLogRepository()
