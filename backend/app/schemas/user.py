"""Pydantic v2 schemas for user profile endpoints."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import AppBaseModel


class UserRead(AppBaseModel):
    """Full user profile returned from GET /users/me."""

    id: UUID
    username: str
    full_name: str
    is_active: bool
    is_email_verified: bool
    is_onboarding_completed: bool
    created_at: datetime
    updated_at: datetime
    gmail_connected: bool = False
    gmail_email: str | None = None
    initial_import_done: bool = False


class UserUpdateRequest(AppBaseModel):
    """Payload for PATCH /users/me — partial update."""

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Updated display name",
    )


class ChangePasswordRequest(AppBaseModel):
    """Payload for POST /users/me/change-password."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    def passwords_match(self) -> bool:
        return self.new_password == self.confirm_password


class DeleteAccountRequest(AppBaseModel):
    """Payload for DELETE /users/me — requires password confirmation."""

    password: str = Field(
        min_length=1,
        max_length=128,
        description="Current password to confirm account deletion",
    )
    confirmation_text: str = Field(
        min_length=6,
        max_length=6,
        description="Must be exactly 'DELETE'",
    )
