"""
Async SQLAlchemy engine, session factory, and dependency provider.

Architecture:
  - create_async_engine: single engine instance for the whole process.
  - async_sessionmaker: factory that creates AsyncSession objects.
  - get_async_session: FastAPI dependency that yields a session per request,
    commits on success, rolls back on exception, and always closes.

Rationale for async:
  FastAPI is async-native. Using sync SQLAlchemy would block the event loop
  during every DB query, destroying concurrency. asyncpg is the fastest
  async PostgreSQL driver for Python.

Connection pool settings:
  - pool_size=10: base number of persistent connections.
  - max_overflow=20: additional connections allowed under peak load.
  - pool_pre_ping=True: validates connections before checkout (handles
    Supabase idle connection timeouts gracefully).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

logger = structlog.get_logger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,           # Log SQL statements in debug mode
    pool_pre_ping=True,            # Validate connection before use
    pool_size=10,                  # Persistent connections
    max_overflow=20,               # Burst capacity
    pool_recycle=1800,             # Recycle connections every 30 minutes
    # pgbouncer (transaction mode) does not support prepared statements.
    # Setting statement_cache_size=0 disables asyncpg's prepared statement cache.
    # See: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#prepared-statement-cache
    connect_args={"statement_cache_size": 0},
)

# ── Session Factory ────────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Don't reload attributes after commit
    autocommit=False,
    autoflush=False,               # Explicit flush for predictable behaviour
)


# ── FastAPI Dependency ─────────────────────────────────────────────────────────
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """
    Yield an AsyncSession for the duration of a single request.

    Usage in route handlers:
        async def my_route(session: AsyncSession = Depends(get_async_session)):

    Commit/rollback is handled here so route handlers stay clean.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    """
    Yield a raw AsyncConnection (for operations that need DDL-level access).
    Rarely needed — prefer get_async_session for all regular queries.
    """
    async with engine.connect() as connection:
        yield connection


async def check_database_health() -> dict[str, Any]:
    """
    Execute a lightweight health check query.
    Used by the /health endpoint and startup validation.
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text("SELECT 1 AS ok")
            )
            row = result.scalar()
            return {"status": "ok", "result": row}
    except Exception as exc:
        logger.error("database_health_check_failed", error=str(exc))
        return {"status": "error", "error": str(exc)}
