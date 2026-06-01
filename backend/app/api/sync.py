"""
Sync API router.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, status
from sse_starlette.sse import EventSourceResponse

from app.core.redis import get_redis
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
