"""
Shared Pydantic v2 schemas used across multiple API modules.

Includes:
- Standard API response envelope (success + data + message)
- Paginated list response
- Error response shape
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ── Base Config ────────────────────────────────────────────────────────────────
class AppBaseModel(BaseModel):
    """
    Project-wide Pydantic base model.

    model_config:
    - from_attributes=True: allows constructing schemas from ORM model instances
      (replaces Pydantic v1's orm_mode=True).
    - populate_by_name=True: accepts both field aliases and Python names.
    - str_strip_whitespace=True: automatically strips leading/trailing whitespace.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


# ── API Response Envelopes ─────────────────────────────────────────────────────
class SuccessResponse(AppBaseModel, Generic[T]):
    """Standard successful response envelope."""

    success: bool = True
    message: str = "OK"
    data: T


class ErrorDetail(AppBaseModel):
    """Structured error detail object."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(AppBaseModel):
    """Standard error response envelope."""

    success: bool = False
    error: ErrorDetail


# ── Pagination ─────────────────────────────────────────────────────────────────
class PaginationParams(AppBaseModel):
    """Query parameters for paginated list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(AppBaseModel, Generic[T]):
    """Paginated list response with metadata."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        total_pages = max(1, -(-total // page_size))  # ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


# ── Health ─────────────────────────────────────────────────────────────────────
class HealthResponse(AppBaseModel):
    status: str = "ok"
    version: str
    environment: str
    database: str = "ok"
