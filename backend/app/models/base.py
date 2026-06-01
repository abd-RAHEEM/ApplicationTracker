"""
SQLAlchemy declarative base and shared model mixins.

All ORM models inherit from Base (for the registry) and TimestampMixin
(for created_at / updated_at columns). UUIDs are the standard primary key type.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Project-wide declarative base.

    All ORM models must inherit from this class so that Alembic
    can discover them via metadata.
    """
    pass


class PrimaryKeyMixin:
    """
    UUID primary key mixin.

    Rationale:
    - UUIDs prevent ID enumeration attacks (sequential int IDs are guessable).
    - gen_random_uuid() generates the value at the DB layer, providing a safe
      fallback if the Python default is not called (e.g. raw INSERT).
    - as_uuid=True maps the column to Python's uuid.UUID type.
    """

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        index=False,  # Primary key index is created automatically
    )


class TimestampMixin:
    """
    Automatic created_at / updated_at timestamps.

    - server_default=func.now() sets the value at the DB layer on INSERT
      (safe for bulk inserts that bypass the ORM).
    - onupdate=func.now() tells SQLAlchemy to set the value on every UPDATE
      issued through the ORM session.
    - timezone=True stores timestamps as TIMESTAMPTZ (UTC-aware).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
