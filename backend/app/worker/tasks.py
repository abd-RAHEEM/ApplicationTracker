"""Celery tasks."""
from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from celery import Task

from app.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """Helper to run async code inside a sync Celery task."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3)
def run_incremental_sync(self, user_id_str: str) -> None:
    """
    Background task to incrementally sync the user's Gmail mailbox.
    Uses async-to-sync translation to call the SyncService.
    """
    logger.info("celery_task_started", task="run_incremental_sync", user_id=user_id_str)
    
    import asyncio
    from uuid import UUID
    from app.services.sync_service import run_sync_for_user

    async def _run():
        await run_sync_for_user(
            user_id=UUID(user_id_str),
            task_id=self.request.id
        )

    try:
        asyncio.run(_run())
        logger.info("celery_task_completed", task="run_incremental_sync", user_id=user_id_str)
    except Exception as e:
        logger.exception("celery_task_failed", task="run_incremental_sync", user_id=user_id_str)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@celery_app.task(bind=True, max_retries=3)
def generate_analytics_task(self, user_id_str: str) -> None:
    """
    Background task to compute and store analytics for a user.
    """
    logger.info("celery_task_started", task="generate_analytics", user_id=user_id_str)
    
    import asyncio
    from uuid import UUID
    from app.db.session import async_session_maker
    from app.services.analytics_service import analytics_service

    async def _run():
        async with async_session_maker() as session:
            await analytics_service.compute_analytics_for_user(
                session=session, 
                user_id=UUID(user_id_str)
            )

    try:
        asyncio.run(_run())
        logger.info("celery_task_completed", task="generate_analytics", user_id=user_id_str)
    except Exception as e:
        logger.exception("celery_task_failed", task="generate_analytics", user_id=user_id_str)
        raise self.retry(exc=e, countdown=10)

@celery_app.task(bind=True, max_retries=3)
def purge_expired_bin_records(self) -> None:
    """
    Periodic task to permanently delete (purge) soft-deleted applications
    whose retention period (purge_after) has expired.
    """
    logger.info("celery_task_started", task="purge_expired_bin_records")
    
    import asyncio
    from datetime import datetime, timezone
    from sqlalchemy import select, delete
    from app.db.session import async_session_maker
    from app.models.deleted_application import DeletedApplication
    from app.models.application import Application

    async def _run():
        async with async_session_maker() as session:
            now = datetime.now(timezone.utc)
            # Find expired entries that haven't been purged
            result = await session.execute(
                select(DeletedApplication)
                .where(
                    DeletedApplication.purge_after <= now,
                    DeletedApplication.is_purged == False
                )
            )
            expired = result.scalars().all()
            
            if not expired:
                logger.info("no_expired_applications_to_purge")
                return
                
            count = 0
            for record in expired:
                # Delete the application record.
                # DB CASCADE will delete the DeletedApplication and status history records.
                await session.execute(
                    delete(Application).where(Application.id == record.application_id)
                )
                count += 1
                
            await session.commit()
            logger.info("purged_expired_applications", count=count)

    try:
        asyncio.run(_run())
        logger.info("celery_task_completed", task="purge_expired_bin_records")
    except Exception as e:
        logger.exception("celery_task_failed", task="purge_expired_bin_records")
        raise self.retry(exc=e, countdown=60)
