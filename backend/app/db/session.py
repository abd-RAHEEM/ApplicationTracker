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

Connection pool — NullPool for pgbouncer:
  Supabase uses pgbouncer in transaction mode as a connection pooler.
  SQLAlchemy's built-in QueuePool keeps long-lived persistent connections
  per process, which conflicts with pgbouncer's transaction-mode assumptions:
    - pgbouncer reuses connections across clients between transactions
    - QueuePool holds them open, exhausting the pgbouncer connection limit
    - asyncpg's prepared statement cache creates DuplicatePreparedStatement errors

  Fix: use NullPool so SQLAlchemy creates/destroys connections per-request
  and pgbouncer handles the actual pooling transparently.
  Also disable asyncpg's prepared statement cache (statement_cache_size=0).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from sqlalchemy.pool import NullPool
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
# NullPool: do NOT pool connections on the SQLAlchemy side.
# pgbouncer (Supabase) is the pooler — SQLAlchemy pooling on top of it causes:
#   - DuplicatePreparedStatementError (asyncpg prepared statement cache conflict)
#   - Connection exhaustion (SQLAlchemy holds connections pgbouncer expects back)
# With NullPool + statement_cache_size=0, each request gets a fresh connection
# from pgbouncer and returns it immediately after the transaction completes.
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,           # Log SQL statements in debug mode
    poolclass=NullPool,            # Let pgbouncer handle pooling (Supabase standard)
    connect_args={"statement_cache_size": 0},  # Disable asyncpg prepared stmt cache
)

# ── Session Factory ────────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Don't reload attributes after commit
    autocommit=False,
    autoflush=False,               # Explicit flush for predictable behaviour
)

async_session_maker = AsyncSessionLocal



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
