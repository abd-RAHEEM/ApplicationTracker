"""Celery application configuration."""
from __future__ import annotations

import os

from celery import Celery

from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "jobtracker_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
