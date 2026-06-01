"""
Gmail OAuth and Onboarding routes.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestException
from app.db.session import get_async_session
from app.dependencies import get_current_user, require_gmail_connected
from app.models.user import User
from app.schemas.gmail import InitialImportConfigRequest, OAuthUrlResponse
from app.services.gmail_oauth_service import gmail_oauth_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/gmail", tags=["Gmail"])


@router.get(
    "/auth-url",
    response_model=OAuthUrlResponse,
    summary="Get Google OAuth Authorization URL",
)
async def get_auth_url(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> OAuthUrlResponse:
    """
    Returns the Google OAuth 2.0 authorization URL for the current user.
    The URL includes a signed CSRF state token.
    Rejects initiation if the user is already connected.
    """
    url = await gmail_oauth_service.get_authorization_url(session, user.id)
    return OAuthUrlResponse(auth_url=url)


@router.get(
    "/callback",
    status_code=status.HTTP_200_OK,
    summary="Google OAuth Callback",
)
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="CSRF state token"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """
    Handle the redirect from Google.
    
    1. Validates the state token.
    2. Exchanges the code for tokens.
    3. Fetches the verified email.
    4. Upserts the Gmail connection.
    5. Marks user's email as verified.
    
    NOTE: In a real app, this might redirect to the frontend rather than returning JSON,
    but returning JSON allows the frontend to pop up a window or handle the flow via API.
    """
    await gmail_oauth_service.handle_oauth_callback(
        session=session,
        user_id=user.id,
        code=code,
        state=state,
    )
    return {"status": "success", "message": "Gmail connected successfully."}


@router.post(
    "/onboarding/complete",
    status_code=status.HTTP_200_OK,
    summary="Complete Initial Import Configuration",
)
async def complete_onboarding(
    payload: InitialImportConfigRequest,
    user: User = Depends(require_gmail_connected),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """
    Complete the onboarding flow by setting the initial import configuration.
    
    Requires an active Gmail connection. Marks the user as fully onboarded,
    unlocking dashboard and application access.
    """
    await gmail_oauth_service.complete_onboarding(
        session=session,
        user_id=user.id,
        import_range=payload.import_range,
        import_from=payload.import_from,
    )
    return {"status": "success", "message": "Onboarding complete."}
