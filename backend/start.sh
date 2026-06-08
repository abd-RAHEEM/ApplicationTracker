#!/bin/bash

# Always run from the directory containing this script.
# This ensures alembic.ini, alembic/ migrations folder, and app/ are all
# on the correct relative paths regardless of how Render invokes this script.
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Starting from directory: $(pwd)"

# Start Celery worker in the background
poetry run celery -A app.worker.celery_app worker --loglevel=info &

# Run database migrations
# Use -c to explicitly name the config file — removes any ambiguity about
# which alembic.ini alembic picks up from the search path.
echo "==> Running Alembic migrations..."
poetry run alembic -c alembic.ini upgrade head
echo "==> Migrations complete."

# Start the FastAPI server
poetry run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
