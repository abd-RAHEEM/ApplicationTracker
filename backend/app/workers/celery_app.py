"""
Celery application factory — Phase 1 placeholder.

Full task implementations are added in Phases 3–5.
This file establishes the Celery app and beat schedule structure.
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings


def create_celery_app() -> Celery:
    """Create and configure the Celery application."""
    app = Celery(
        "jobtracker",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "app.workers.initial_import",     # Phase 3
            "app.workers.incremental_sync",   # Phase 4
            "app.workers.analytics",          # Phase 6
            "app.workers.bin_cleanup",        # Phase 7
        ],
    )

    app.conf.update(
        # Serialisation
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        # Timezones
        timezone="UTC",
        enable_utc=True,
        # Task behaviour
        task_acks_late=True,              # Acknowledge AFTER task completes (safer)
        task_reject_on_worker_lost=True,  # Re-queue if worker crashes mid-task
        worker_prefetch_multiplier=1,     # One task per worker at a time (fairness)
        # Result TTL
        result_expires=3600,              # Clean up results after 1 hour
        # Queues
        task_default_queue="default",
        task_queues={
            "default": {},
            "email_processing": {},
            "scheduled": {},
        },
        # Task routing
        task_routes={
            "app.workers.initial_import.*": {"queue": "email_processing"},
            "app.workers.incremental_sync.*": {"queue": "email_processing"},
            "app.workers.analytics.*": {"queue": "default"},
            "app.workers.bin_cleanup.*": {"queue": "scheduled"},
        },
        # Beat schedule (on-demand sync only — no auto-polling per spec)
        beat_schedule={
            "purge-expired-bin-items": {
                "task": "app.workers.bin_cleanup.purge_expired_bin_task",
                "schedule": crontab(hour="*/6"),  # Every 6 hours
                "options": {"queue": "scheduled"},
            },
        },
    )

    return app


celery_app = create_celery_app()
