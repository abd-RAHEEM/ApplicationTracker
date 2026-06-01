"""
FastAPI application factory.

main.py is the entrypoint for Uvicorn. It creates the FastAPI app,
registers middleware, mounts routers, and registers exception handlers.

Pattern:
  create_app() is a factory so tests can create isolated app instances.
  The module-level `app` is the instance used by the Uvicorn server.
"""
from __future__ import annotations

import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging
from app.core.rate_limiter import limiter
from app.db.session import check_database_health

logger = structlog.get_logger(__name__)



def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI app with:
    - Structured logging
    - CORS middleware
    - Rate limiting (SlowAPI)
    - Custom exception handlers
    - API routers
    - Startup / shutdown lifecycle events
    """
    # Configure logging before anything else
    configure_logging()

    app = FastAPI(
        title="ApplicationTracker API",
        version="0.1.0",
        description="Backend API for ApplicationTracker platform",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # ── Rate Limiter ────────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── CORS ────────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,     # Required for cookie-based auth
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "X-Requested-With"],
        expose_headers=["X-Request-ID"],
    )

    # ── Request ID Middleware ───────────────────────────────────────────────────
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Attach a unique request ID to every request for log correlation."""
        import uuid
        import structlog.contextvars

        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ── Exception Handlers ──────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ─────────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Health Check ─────────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health() -> dict:
        db_status = await check_database_health()
        return {
            "status": "ok",
            "version": settings.app_version,
            "environment": settings.environment,
            "database": db_status["status"],
        }

    # ── Lifecycle Events ─────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info(
            "application_starting",
            name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
        )
        db_health = await check_database_health()
        if db_health["status"] != "ok":
            logger.critical("database_unreachable_on_startup", detail=db_health)
        else:
            logger.info("database_connected")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("application_shutting_down")
        from app.db.session import engine
        await engine.dispose()

    return app


# ── Application Instance ───────────────────────────────────────────────────────
app: FastAPI = create_app()
