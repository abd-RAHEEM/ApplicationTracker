"""
Gmail OAuth and Onboarding routes.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestException
from app.db.session import get_async_session
from app.dependencies import get_current_user, get_optional_user, require_gmail_connected
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
    summary="Google OAuth Callback — redirects back to frontend",
)
async def oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="CSRF state token"),
    error: str | None = Query(None, description="Error from Google (user denied)"),
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_async_session),
) -> RedirectResponse:
    """
    Handle the redirect from Google after the user grants/denies permission.

    On success  → redirects browser to {FRONTEND_URL}/onboarding/import-config
    On failure  → redirects browser to {FRONTEND_URL}/onboarding/connect-gmail?error=...
    """
    frontend_url = settings.frontend_url.rstrip("/")

    # If the user is unauthenticated (e.g. because Google redirected directly to the
    # backend domain, where cookies are blocked as cross-origin on Render subdomains),
    # we redirect the browser to the frontend proxy callback to retrieve cookies.
    if not user:
        if "proxied" in request.query_params:
            logger.warning("gmail_oauth_callback_failed_no_session")
            return RedirectResponse(
                url=f"{frontend_url}/onboarding/connect-gmail?error=session_expired",
                status_code=302,
            )
        
        logger.info("gmail_oauth_callback_redirecting_to_proxy")
        proxy_url = f"{frontend_url}/api/v1/gmail/callback?code={code}&state={state}&proxied=true"
        if error:
            proxy_url += f"&error={error}"
        return RedirectResponse(url=proxy_url, status_code=302)

    # Handle user-denied or Google error
    if error:
        logger.warning("gmail_oauth_denied_by_user", error=error)
        return RedirectResponse(
            url=f"{frontend_url}/onboarding/connect-gmail?error=access_denied",
            status_code=302,
        )

    try:
        await gmail_oauth_service.handle_oauth_callback(
            session=session,
            user_id=user.id,
            code=code,
            state=state,
        )
    except Exception as exc:
        logger.error("gmail_oauth_callback_failed", error=str(exc))
        return RedirectResponse(
            url=f"{frontend_url}/onboarding/connect-gmail?error=oauth_failed",
            status_code=302,
        )

    # Success — redirect to next onboarding step
    return RedirectResponse(
        url=f"{frontend_url}/onboarding/import-config?gmail=connected",
        status_code=302,
    )


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
