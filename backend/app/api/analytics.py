"""Analytics API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.dependencies import get_current_user
from app.models.application_analytics import ApplicationAnalytics
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Get user analytics",
)
async def get_analytics(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Returns the precomputed analytics for the user.
    """
    result = await session.execute(
        select(ApplicationAnalytics).where(ApplicationAnalytics.user_id == user.id)
    )
    analytics = result.scalars().first()
    
    if not analytics:
        # Return default empty values
        return {
            "total_applications": 0,
            "applied_count": 0,
            "assessment_count": 0,
            "interview_count": 0,
            "offer_count": 0,
            "rejected_count": 0,
            "pending_count": 0,
            "interview_rate": 0.0,
            "offer_rate": 0.0,
            "response_rate": 0.0,
            "monthly_data": [],
            "computed_at": None,
        }
        
    total = analytics.total_applications
    interviews = analytics.interview_count
    offers = analytics.offer_count
    rejections = analytics.rejected_count
    
    response_rate = ((interviews + offers + rejections) / total) * 100 if total > 0 else 0.0
        
    return {
        "total_applications": analytics.total_applications,
        "applied_count": analytics.applied_count,
        "assessment_count": analytics.assessment_count,
        "interview_count": analytics.interview_count,
        "offer_count": analytics.offer_count,
        "rejected_count": analytics.rejected_count,
        "pending_count": analytics.pending_count,
        "interview_rate": analytics.interview_rate,
        "offer_rate": analytics.offer_rate,
        "response_rate": round(response_rate, 2),
        "monthly_data": analytics.monthly_data or [],
        "computed_at": analytics.computed_at.isoformat() if analytics.computed_at else None,
    }
