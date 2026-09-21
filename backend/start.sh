#!/bin/bash
set -e

# Always run from the directory containing this script.
# This ensures alembic.ini, alembic/ migrations folder, and app/ are all
# on the correct relative paths regardless of how Render invokes this script.
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Starting from directory: $(pwd)"

# ── Database Migrations ───────────────────────────────────────────────────────
echo "==> Running Alembic migrations..."
poetry run alembic -c alembic.ini upgrade head
echo "==> Migrations complete."

# ── Optional Inline Celery Worker ─────────────────────────────────────────────
# Concurrency is capped at 1 to prevent OOM on 512 MB Render containers.
# If a separate Render Background Worker is configured, set RUN_INLINE_CELERY=false.
if [ "${RUN_INLINE_CELERY:-true}" = "true" ]; then
    echo "==> Launching inline Celery worker (concurrency=1)..."
    poetry run celery -A app.worker.celery_app worker \
        --loglevel=info \
        -B \
        --concurrency=1 \
        --max-tasks-per-child=20 &
    echo "==> Inline Celery worker launched in background"
fi

# ── FastAPI Server ────────────────────────────────────────────────────────────
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
