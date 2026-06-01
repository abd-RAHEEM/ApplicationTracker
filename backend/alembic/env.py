"""
Alembic environment configuration.

Uses the DATABASE_URL_SYNC env var for migrations (sync psycopg3 driver).
All models are imported via app.models so Alembic can auto-detect schema changes.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import all models so Alembic can see them in metadata
from app.models import Base  # noqa: F401 — registers all tables

# ── Alembic config object ──────────────────────────────────────────────────────
alembic_cfg = context.config

# Set the database URL from environment variable (not alembic.ini)
# This keeps credentials out of version control.
database_url_sync = os.environ.get("DATABASE_URL_SYNC")
if not database_url_sync:
    raise RuntimeError(
        "DATABASE_URL_SYNC environment variable is not set. "
        "Set it to a psycopg3 sync URL: postgresql+psycopg://..."
    )
alembic_cfg.set_main_option("sqlalchemy.url", database_url_sync)

# Set up logging from the alembic.ini [loggers] section
if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

# Target metadata for auto-generate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without a live database connection.
    Useful for review or applying migrations via a DBA.
    """
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode with a live database connection.

    This is the standard mode used in CI/CD pipelines.
    """
    connectable = engine_from_config(
        alembic_cfg.get_section(alembic_cfg.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,      # No connection pooling for migrations
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,          # Detect column type changes
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
