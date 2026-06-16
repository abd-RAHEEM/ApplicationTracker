"""Redis dependency for caching and Pub/Sub (SSE)."""
from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

# Global redis connection pool
redis_client = aioredis.from_url(
    settings.redis_url, 
    encoding="utf-8", 
    decode_responses=True,
    health_check_interval=30,      # Prevents idle connection drops on serverless Redis (e.g. Upstash)
    retry_on_timeout=True,         # Auto-reconnect and retry once on timeout/connection drops
    socket_timeout=5.0,            # Bounded socket timeout to prevent blocking FastAPI indefinitely
    socket_connect_timeout=5.0,    # Connect timeout
    socket_keepalive=True          # TCP keepalive probes
)

async def get_redis() -> aioredis.Redis:
    """Dependency provider for Redis."""
    return redis_client

async def publish_sse_event(user_id: str, event_data: str) -> None:
    """Publish an SSE event to a user-specific Redis channel."""
    channel = f"sse:user:{user_id}"
    await redis_client.publish(channel, event_data)
