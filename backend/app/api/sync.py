"""
Sync API router.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.db.session import get_async_session
from app.dependencies import get_current_user, require_gmail_connected
from app.models.user import User
from app.worker.tasks import run_incremental_sync

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post(
    "/now",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Manual Sync",
)
async def trigger_manual_sync(
    user: User = Depends(require_gmail_connected),
) -> dict[str, str]:
    """
    Manually queues a background task to sync the user's emails.
    Does not block the request. Client should connect to /events for status.
    """
    run_incremental_sync.delay(str(user.id))
    return {"status": "accepted", "message": "Sync queued."}


@router.post(
    "/reparse",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reset and Re-parse All Emails",
)
async def reparse_emails(
    user: User = Depends(require_gmail_connected),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """
    Resets all previously-parsed emails back to unparsed state and immediately
    re-runs the parser pipeline.  Useful after parser logic improvements.

    Does NOT re-fetch emails from Gmail — it re-parses what is already stored.
    """
    from app.models.email import Email

    # Reset every email for this user
    await session.execute(
        update(Email)
        .where(Email.user_id == user.id)
        .values(is_parsed=False, parse_attempts=0, last_parse_error=None, parsed_at=None)
    )
    await session.commit()

    # Run parser in background via Celery
    from app.worker.tasks import reparse_emails_task
    reparse_emails_task.delay(str(user.id))

    return {
        "status": "accepted",
        "message": "All emails queued for re-parsing. Connect to /sync/events for progress.",
    }


@router.post(
    "/reset-initial",
    status_code=status.HTTP_200_OK,
    summary="Reset Initial Import — Re-fetch Full Historical Window",
)
async def reset_initial_import(
    user: User = Depends(require_gmail_connected),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """
    Resets the initial import flag so the NEXT sync re-fetches ALL emails
    from the user's originally-chosen date window (e.g. last 6 months).

    Use this when:
    - The initial sync ran but parsing was broken (no applications created).
    - You want to force a full historical re-fetch from Gmail.

    After calling this, trigger a sync via POST /sync/now.
    """
    from sqlalchemy import update
    from app.models.gmail_connection import GmailConnection

    await session.execute(
        update(GmailConnection)
        .where(GmailConnection.user_id == user.id)
        .values(
            initial_import_done=False,
            last_successful_sync_at=None,   # Force full re-fetch from initial_import_from
        )
    )
    await session.commit()

    return {
        "status": "ok",
        "message": (
            "Initial import reset. Trigger POST /sync/now to re-fetch your "
            "full email history from the original date window."
        ),
    }


@router.get(
    "/events",
    summary="Server-Sent Events for Sync Progress",
)
async def sync_events(
    user: User = Depends(get_current_user),
    redis=Depends(get_redis),
) -> EventSourceResponse:
    """
    SSE endpoint streaming real-time sync progress.
    """
    channel = f"sse:user:{user.id}"

    async def event_generator() -> AsyncGenerator[dict, None]:
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None:
                    # Yield standard SSE format
                    yield {"data": message["data"]}
                else:
                    # Give control back to event loop
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(channel)
            raise

    return EventSourceResponse(event_generator())

