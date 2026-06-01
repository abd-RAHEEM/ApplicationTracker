"""
Structured logging configuration using structlog.

All log output is JSON-formatted in production (machine-parseable by
log aggregators like Datadog / Papertrail) and human-readable with colours
in development.

Usage anywhere in the codebase:
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("user_registered", user_id=str(user.id), username=user.username)

Design decisions:
- structlog over standard logging: adds key=value context binding, which is
  dramatically more useful in distributed systems than format strings.
- JSON renderer in production: log aggregators can index individual fields.
- ConsoleRenderer in development: colourised, readable output.
- add_log_level + timestamper are mandatory for log triage.
"""
from __future__ import annotations

import logging
import sys

import structlog

from app.config import settings


def configure_logging() -> None:
    """
    Configure structlog and the standard library logging bridge.

    Call this exactly once at application startup in main.py.
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,     # Thread/task-local context
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        # JSON output for log aggregators
        renderer = structlog.processors.JSONRenderer()
    else:
        # Human-readable colourised output for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *shared_processors,
            renderer,
        ]
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Root logger receives everything; individual loggers can override level
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, settings.log_level, logging.INFO))

    # Silence noisy third-party loggers in non-debug mode
    if not settings.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
