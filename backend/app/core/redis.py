"""Redis dependency for caching and Pub/Sub (SSE)."""
from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

# Global redis connection pool
redis_client = aioredis.from_url(
    settings.redis_url, 
    encoding="utf-8", 
    decode_responses=True
)

async def get_redis() -> aioredis.Redis:
    """Dependency provider for Redis."""
    return redis_client

async def publish_sse_event(user_id: str, event_data: str) -> None:
    """Publish an SSE event to a user-specific Redis channel."""
    channel = f"sse:user:{user_id}"
    await redis_client.publish(channel, event_data)
