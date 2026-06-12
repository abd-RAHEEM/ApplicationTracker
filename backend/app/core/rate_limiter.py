"""
SlowAPI rate limiter configuration.

SlowAPI wraps limits as a FastAPI middleware and supports per-endpoint
and per-IP rate limits backed by Redis or in-memory storage.

Rationale for rate limiting on auth endpoints:
- Login: prevents credential stuffing attacks.
- Register: prevents spam account creation.
- Password reset: prevents email flooding / enumeration via timing.
- Sync: prevents accidental or malicious Gmail API quota exhaustion.
"""
from __future__ import annotations

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings


def _get_key(request) -> str:  # type: ignore[no-untyped-def]
    """
    Rate limit key function.

    Falls back to IP address if user is not authenticated.
    Resolves X-Forwarded-For for reverse proxy environments.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return get_remote_address(request)


# Shared limiter instance — imported by route modules
limiter = Limiter(key_func=_get_key)

# Export the SlowAPI error handler for registration in main.py
rate_limit_exceeded_handler = _rate_limit_exceeded_handler

# Shorthand limit strings (from settings, overridable per environment)
LOGIN_RATE_LIMIT: str = settings.rate_limit_login
REGISTER_RATE_LIMIT: str = settings.rate_limit_register
PASSWORD_RESET_RATE_LIMIT: str = settings.rate_limit_password_reset
SYNC_RATE_LIMIT: str = settings.rate_limit_sync
