import asyncio
import inspect
import redis.asyncio as aioredis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError

from app.config import settings

# Configure retry logic for resilient connection management (especially for serverless Redis like Upstash)
redis_retry = Retry(ExponentialBackoff(), 3)

# Global raw redis connection pool
redis_kwargs = {
    "encoding": "utf-8",
    "decode_responses": True,
    "retry": redis_retry,
    "health_check_interval": 30,      # Prevents idle connection drops on serverless Redis (e.g. Upstash)
    "retry_on_timeout": True,         # Auto-reconnect and retry once on timeout/connection drops
    "socket_timeout": 5.0,            # Bounded socket timeout to prevent blocking FastAPI indefinitely
    "socket_connect_timeout": 5.0,    # Connect timeout
    "socket_keepalive": True,         # TCP keepalive probes
    "max_connections": 10             # Limit pool size to prevent exceeding Upstash free connection limits
}

if settings.redis_url.startswith("rediss://"):
    redis_kwargs["ssl_cert_reqs"] = "none"   # Disable SSL verification to match Celery and prevent drops on Upstash

_raw_redis_client = aioredis.from_url(settings.redis_url, **redis_kwargs)

class ResilientRedis:
    """
    Wrapper around the raw Redis client to catch and retry connection/timeout errors 
    that escape the connection pool during get_connection() or command execution.
    """
    def __init__(self, client: aioredis.Redis):
        self._client = client

    def __getattr__(self, name: str):
        attr = getattr(self._client, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                res = attr(*args, **kwargs)
                if inspect.iscoroutine(res):
                    async def execute_with_retry():
                        current_res = res
                        retries = 3
                        delay = 0.5
                        for attempt in range(retries):
                            try:
                                return await current_res
                            except (ConnectionError, TimeoutError):
                                if attempt == retries - 1:
                                    raise
                                # Close/disconnect to rebuild connection
                                try:
                                    await self._client.connection_pool.disconnect()
                                except Exception:
                                    pass
                                await asyncio.sleep(delay * (2 ** attempt))
                                current_res = attr(*args, **kwargs)
                    return execute_with_retry()
                return res
            return wrapper
        return attr

# Resilient global Redis client wrapping the raw one
redis_client = ResilientRedis(_raw_redis_client)

async def get_redis() -> aioredis.Redis:
    """Dependency provider for Redis."""
    return redis_client

async def publish_sse_event(user_id: str, event_data: str) -> None:
    """Publish an SSE event to a user-specific Redis channel."""
    channel = f"sse:user:{user_id}"
    await redis_client.publish(channel, event_data)
