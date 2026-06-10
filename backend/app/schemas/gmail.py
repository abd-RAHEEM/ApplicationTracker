"""
Schemas for Gmail OAuth and Onboarding flow.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, validator

from app.schemas.common import AppBaseModel


class OAuthUrlResponse(AppBaseModel):
    """Response containing the Google OAuth authorization URL."""
    auth_url: str = Field(..., description="Redirect user to this URL")


class InitialImportConfigRequest(AppBaseModel):
    """Payload to configure the initial historical import."""
    import_range: str = Field(
        ...,
        description="The selected historical range (e.g. 1m, 3m, 6m)",
    )
    import_from: datetime = Field(
        ...,
        description="The starting date for historical email import",
    )


class GmailConnectionRead(AppBaseModel):
    """Public representation of a user's Gmail connection."""
    gmail_email: str
    is_active: bool
    connected_at: datetime
    last_successful_sync_at: datetime | None
    initial_import_done: bool
    initial_import_from: datetime | None
