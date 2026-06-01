"""
User profile routes — /v1/users/*

Handles:
  - GET  /users/me         — fetch own profile
  - PATCH /users/me        — update display name
  - POST /users/me/change-password — change password (authenticated)
  - DELETE /users/me       — soft-delete own account
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.db.session import get_async_session
from app.dependencies import get_current_user, get_session_id
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.repositories.gmail_repository import gmail_repository
from app.schemas.common import SuccessResponse
from app.schemas.user import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    UserRead,
    UserUpdateRequest,
)
from app.services.auth_service import auth_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


async def _build_user_read(
    user: User,
    session: AsyncSession,
) -> UserRead:
    """Build UserRead schema with Gmail connection status."""
    gmail = await gmail_repository.get_active_connection(session, user.id)
    return UserRead(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        is_onboarding_completed=user.is_onboarding_completed,
        created_at=user.created_at,
        updated_at=user.updated_at,
        gmail_connected=gmail is not None,
        gmail_email=gmail.gmail_email if gmail else None,
        initial_import_done=gmail.initial_import_done if gmail else False,
    )


# ── GET /users/me ──────────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=SuccessResponse[UserRead],
    summary="Get the authenticated user's profile",
)
async def get_me(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[UserRead]:
    """Return the current user's profile including Gmail connection status."""
    user_read = await _build_user_read(current_user, session)
    return SuccessResponse(data=user_read)


# ── PATCH /users/me ────────────────────────────────────────────────────────────
@router.patch(
    "/me",
    response_model=SuccessResponse[UserRead],
    summary="Update display name",
)
async def update_me(
    body: UserUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[UserRead]:
    """
    Partial update for the user's own profile.
    Currently supports updating full_name only.
    """
    if not body.full_name:
        raise BadRequestException(message="Nothing to update")

    updated_user = await user_repository.update(
        session, current_user, full_name=body.full_name
    )
    user_read = await _build_user_read(updated_user, session)
    return SuccessResponse(data=user_read, message="Profile updated successfully")


# ── POST /users/me/change-password ────────────────────────────────────────────
@router.post(
    "/me/change-password",
    response_model=SuccessResponse[dict],
    summary="Change password (requires current password)",
)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[dict]:
    """
    Change the authenticated user's password.

    Requires current password for verification.
    Revokes ALL sessions after update — user must re-login everywhere.
    """
    if not body.passwords_match():
        raise BadRequestException(message="New passwords do not match")

    await auth_service.change_password(
        session=session,
        user_id=current_user.id,
        current_password=body.current_password,
        new_password=body.new_password,
    )

    # Clear cookies — force re-login
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")

    return SuccessResponse(
        data={},
        message="Password changed. Please log in with your new password.",
    )


# ── DELETE /users/me ───────────────────────────────────────────────────────────
@router.delete(
    "/me",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete account (permanent deletion — requires password and confirmation)",
)
async def delete_account(
    body: DeleteAccountRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[dict]:
    """
    Permanently delete the user's account and all associated data.
    """
    if body.confirmation_text != "DELETE":
        raise BadRequestException(message="Confirmation text must be 'DELETE'")

    await auth_service.delete_account(
        session=session,
        user_id=current_user.id,
        password=body.password,
    )

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")

    return SuccessResponse(
        data={},
        message="Account has been permanently deleted.",
    )
