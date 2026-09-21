"""
SlowAPI rate limiter configuration.

SlowAPI wraps limits as a FastAPI middleware and supports per-endpoint
and per-IP rate limits backed by Redis or in-memory storage.

Rationale for rate limiting on auth endpoints:
- Login: prevents credential stuffing attacks.
- Register: prevents spam account creation.
- Password reset: prevents email flooding / enumeration via timing.
- Sync: prevents accidental or malicious Gmail API quota exhaustion.

⚠️  Proxy-aware IP resolution:
On hosted platforms (Render, Railway, Fly.io) the app sits behind a reverse
proxy.  SlowAPI's default get_remote_address() returns the proxy's IP, which
causes ALL users to share the same rate-limit bucket — a single user can lock
out everyone.

Our _get_key() resolves the real client IP from X-Forwarded-For when present,
but only trusts the first (leftmost) hop which is the genuine client IP as set
by the load balancer.  Direct access without a proxy falls back to
request.client.host.
"""
from __future__ import annotations

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings


def get_client_ip(request) -> str:  # type: ignore[no-untyped-def]
    """
    Proxy-aware client IP resolution.

    Priority:
    1. X-Forwarded-For leftmost entry (set by load balancer / reverse proxy)
    2. X-Real-IP header (Nginx / proxy convention)
    3. request.client.host (direct connection)
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    real_ip = request.headers.get("x-real-ip")
    client_host = request.client.host if request.client else None

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if real_ip:
        return real_ip.strip()
    return client_host or "unknown"


def _get_key(request) -> str:  # type: ignore[no-untyped-def]
    """Rate limit key function using resolved client IP."""
    return get_client_ip(request)


# Shared limiter instance — Redis-backed in production, in-memory in dev/testing
storage_uri = settings.redis_url if settings.is_production else "memory://"
limiter = Limiter(key_func=_get_key, storage_uri=storage_uri)

# Export the SlowAPI error handler for registration in main.py
rate_limit_exceeded_handler = _rate_limit_exceeded_handler

# Shorthand limit strings (from settings, overridable per environment)
LOGIN_RATE_LIMIT: str = settings.rate_limit_login
REGISTER_RATE_LIMIT: str = settings.rate_limit_register
PASSWORD_RESET_RATE_LIMIT: str = settings.rate_limit_password_reset
SYNC_RATE_LIMIT: str = settings.rate_limit_sync
REFRESH_RATE_LIMIT: str = settings.rate_limit_refresh
