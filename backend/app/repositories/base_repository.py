"""
Generic base repository implementing common CRUD operations.

All entity repositories extend this class and inherit:
- get_by_id
- create
- update
- delete (hard delete — soft delete is in subclasses)
- exists

Design:
- Generic[T] with a concrete model type makes repositories fully typed.
- All methods accept AsyncSession explicitly (dependency injection from FastAPI).
  There is NO global session state — each request gets its own session.
- flush() is used instead of commit() so that multiple repository operations
  within a single request participate in the same transaction (committed by
  get_async_session on success, rolled back on failure).
"""
from __future__ import annotations

from typing import Any, Generic, Type, TypeVar
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic CRUD repository.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self) -> None:
                super().__init__(User)
    """

    def __init__(self, model: Type[T]) -> None:
        self.model = model

    async def get_by_id(self, session: AsyncSession, id: UUID) -> T | None:
        """Fetch a record by primary key. Returns None if not found."""
        result = await session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, **kwargs: Any) -> T:
        """
        Create and persist a new record.

        Calls flush() so the record gets a DB-generated ID immediately,
        but the transaction is not committed until the request completes.
        """
        instance = self.model(**kwargs)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        logger.debug(
            "record_created",
            model=self.model.__name__,
            id=str(getattr(instance, "id", None)),
        )
        return instance

    async def update(
        self, session: AsyncSession, instance: T, **kwargs: Any
    ) -> T:
        """
        Update fields on an existing record.

        Only fields explicitly passed are modified (partial update pattern).
        """
        for key, value in kwargs.items():
            setattr(instance, key, value)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def delete(self, session: AsyncSession, instance: T) -> None:
        """Hard delete a record from the database."""
        await session.delete(instance)
        await session.flush()
        logger.debug(
            "record_deleted",
            model=self.model.__name__,
            id=str(getattr(instance, "id", None)),
        )

    async def exists(self, session: AsyncSession, **filters: Any) -> bool:
        """Return True if at least one record matching the filters exists."""
        conditions = [
            getattr(self.model, k) == v for k, v in filters.items()
        ]
        result = await session.execute(
            select(func.count()).select_from(
                select(self.model).where(*conditions).subquery()
            )
        )
        return (result.scalar() or 0) > 0

    async def count(self, session: AsyncSession, **filters: Any) -> int:
        """Return the count of records matching the given filters."""
        conditions = [
            getattr(self.model, k) == v for k, v in filters.items()
        ]
        stmt = select(func.count()).select_from(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        result = await session.execute(stmt)
        return result.scalar() or 0
