"""Celery application configuration."""
from __future__ import annotations

import ssl
from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "jobtracker_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_conf: dict = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "beat_schedule": {
        "purge-expired-bin-items": {
            "task": "app.worker.tasks.purge_expired_bin_records",
            "schedule": crontab(hour="*/6"),  # Run every 6 hours
        },
    },
}

if settings.redis_url.startswith("rediss://"):
    celery_conf["broker_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_conf["redis_backend_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_NONE}

celery_app.conf.update(celery_conf)
