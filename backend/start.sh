#!/bin/bash

# Start Celery worker in the background
poetry run celery -A app.worker.celery_app worker --loglevel=info &

# Run database migrations
poetry run alembic upgrade head

# Start the FastAPI server
poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT
