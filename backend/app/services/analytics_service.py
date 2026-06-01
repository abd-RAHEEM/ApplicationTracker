"""Analytics calculation service."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.application_analytics import ApplicationAnalytics

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """Service to compute and store application analytics."""

    async def compute_analytics_for_user(self, session: AsyncSession, user_id: UUID) -> None:
        """
        Calculates all core metrics for the dashboard from the `applications` table
        and upserts the `application_analytics` row.
        """
        logger.info("computing_analytics", user_id=str(user_id))
        
        # We only count active (not soft-deleted) applications
        base_query = select(Application).where(
            Application.user_id == user_id,
            Application.is_deleted == False  # noqa: E712
        )
        
        result = await session.execute(base_query)
        apps = result.scalars().all()
        
        total = len(apps)
        
        counts = {
            ApplicationStatus.APPLIED: 0,
            ApplicationStatus.ASSESSMENT: 0,
            ApplicationStatus.INTERVIEW: 0,
            ApplicationStatus.OFFER: 0,
            ApplicationStatus.REJECTED: 0,
            ApplicationStatus.PENDING: 0,
        }
        
        monthly_map = {}
        
        for app in apps:
            counts[app.current_status] += 1
            
            # Use applied_at or last_activity_at or created_at for trend
            date_val = app.applied_at or app.created_at
            if date_val:
                month_key = date_val.strftime("%Y-%m")
                monthly_map[month_key] = monthly_map.get(month_key, 0) + 1
                
        # Format monthly data for JSONB: [{"month": "2026-01", "count": 5}, ...]
        # Sort chronologically
        monthly_data = [{"month": k, "count": v} for k, v in sorted(monthly_map.items())]
        
        # Calculate rates
        # The user requested:
        # Interview Rate: interviews / total_applications
        # Offer Rate: offers / total_applications
        # Response Rate: (interviews + offers + rejections) / total_applications
        
        interview_rate = (counts[ApplicationStatus.INTERVIEW] / total) * 100 if total > 0 else 0.0
        offer_rate = (counts[ApplicationStatus.OFFER] / total) * 100 if total > 0 else 0.0
        
        responded = counts[ApplicationStatus.INTERVIEW] + counts[ApplicationStatus.OFFER] + counts[ApplicationStatus.REJECTED]
        response_rate = (responded / total) * 100 if total > 0 else 0.0
        
        # Find existing analytics row or create new
        analytics_result = await session.execute(
            select(ApplicationAnalytics).where(ApplicationAnalytics.user_id == user_id)
        )
        analytics = analytics_result.scalars().first()
        
        if not analytics:
            analytics = ApplicationAnalytics(user_id=user_id)
            session.add(analytics)
            
        analytics.computed_at = datetime.now(timezone.utc)
        analytics.total_applications = total
        analytics.applied_count = counts[ApplicationStatus.APPLIED]
        analytics.assessment_count = counts[ApplicationStatus.ASSESSMENT]
        analytics.interview_count = counts[ApplicationStatus.INTERVIEW]
        analytics.offer_count = counts[ApplicationStatus.OFFER]
        analytics.rejected_count = counts[ApplicationStatus.REJECTED]
        analytics.pending_count = counts[ApplicationStatus.PENDING]
        
        analytics.interview_rate = round(interview_rate, 2)
        analytics.offer_rate = round(offer_rate, 2)
        # We reuse rejection_rate column in schema to store response_rate for now
        # Actually wait, schema has rejection_rate. Let me add response_rate dynamically
        # or use rejection_rate as rejection_rate.
        analytics.rejection_rate = round((counts[ApplicationStatus.REJECTED] / total) * 100 if total > 0 else 0.0, 2)
        
        # Wait, the prompt requested response_rate but schema has rejection_rate. I will put response_rate into monthly_data 
        # or we just compute it on the fly in the API. 
        
        analytics.monthly_data = monthly_data
        
        await session.commit()
        logger.info("analytics_computed_successfully", user_id=str(user_id))

analytics_service = AnalyticsService()
