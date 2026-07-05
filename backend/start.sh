#!/bin/bash
set -e

# Always run from the directory containing this script.
# This ensures alembic.ini, alembic/ migrations folder, and app/ are all
# on the correct relative paths regardless of how Render invokes this script.
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Starting from directory: $(pwd)"

# ── Celery Worker ─────────────────────────────────────────────────────────────
# Concurrency is capped at 2 to stay within the 512 MB Render free-tier RAM.
# Each prefork worker is a separate process; too many workers = OOM.
# -B runs celery-beat (scheduler) inside the same process to save one more
# process slot.
# --max-tasks-per-child prevents long-running worker processes from leaking
# memory over time.
poetry run celery -A app.worker.celery_app worker \
    --loglevel=info \
    -B \
    --concurrency=2 \
    --max-tasks-per-child=50 &

# ── Database Migrations ───────────────────────────────────────────────────────
echo "==> Running Alembic migrations..."
poetry run alembic -c alembic.ini upgrade head || echo "==> WARNING: Alembic migrations failed!"
echo "==> Migrations complete."

# ── FastAPI Server ────────────────────────────────────────────────────────────
# WEB_CONCURRENCY is set by Render based on available CPUs; default 1 on free tier.
poetry run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
