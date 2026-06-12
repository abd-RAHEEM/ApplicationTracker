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


# ── Dialect-Agnostic Types for Testing Compatibility ──────────────────────────
from sqlalchemy.types import TypeDecorator, CHAR, Text, JSON
from sqlalchemy.dialects.postgresql import (
    INET as PG_INET,
    ARRAY as PG_ARRAY,
    JSONB as PG_JSONB,
)
import json


class INET(TypeDecorator):
    """Dialect-agnostic INET type. Compiles to PostgreSQL INET, CHAR(45) otherwise."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_INET())
        else:
            return dialect.type_descriptor(CHAR(45))


class ARRAY_Compatible(TypeDecorator):
    """Dialect-agnostic ARRAY type. Uses PG ARRAY on postgresql, JSON text on other dialects."""
    impl = Text
    cache_ok = True

    def __init__(self, item_type):
        super().__init__()
        self.item_type = item_type

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(self.item_type))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if not value or value == "{}":
            return []
        try:
            return json.loads(value)
        except Exception:
            return []


class JSONB(TypeDecorator):
    """Dialect-agnostic JSONB type. Compiles to PostgreSQL JSONB, JSON otherwise."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        else:
            return dialect.type_descriptor(JSON())
