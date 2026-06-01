"""Application creation and deduplication logic."""
from __future__ import annotations

from uuid import UUID
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.status_history import ApplicationStatusHistory, StatusSource
from app.schemas.parser import NormalizedEvent

logger = structlog.get_logger(__name__)


class ApplicationService:
    """Business logic for applications."""

    async def process_normalized_event(
        self, session: AsyncSession, user_id: UUID, event: NormalizedEvent
    ) -> None:
        """
        Takes a NormalizedEvent from the parser and either creates a new Application
        or updates an existing one based on deduplication rules.
        """
        # 1. Deduplication (Primary: thread_id, Secondary: company similarity)
        # Note: The user requested that deduplication must ALWAYS include company matching.
        # We will check if an application exists for this user with this thread ID AND matching company,
        # OR just matching company (and role if possible) if thread ID doesn't match.
        
        existing_app = None
        
        # Try finding by thread_id first
        if event.gmail_thread_id:
            result = await session.execute(
                select(Application)
                .where(
                    Application.user_id == user_id,
                    Application.gmail_thread_id == event.gmail_thread_id,
                    Application.is_deleted == False  # noqa: E712
                )
            )
            thread_app = result.scalars().first()
            if thread_app:
                # User constraint: "Deduplication must always include company matching."
                # We do a basic string inclusion/similarity check.
                if self._company_match(thread_app.company_name, event.company):
                    existing_app = thread_app
                    
        # If not found by thread, try secondary matching (Company + Role)
        if not existing_app:
            # Look for recent applications with the same company and role
            result = await session.execute(
                select(Application)
                .where(
                    Application.user_id == user_id,
                    Application.is_deleted == False  # noqa: E712
                )
                .order_by(Application.last_activity_at.desc())
                .limit(50) # Bounded search
            )
            apps = result.scalars().all()
            for app in apps:
                if self._company_match(app.company_name, event.company):
                    # Also check role similarity to avoid merging separate roles at same company
                    if self._role_match(app.role_title, event.role):
                        existing_app = app
                        break
                        
        if existing_app:
            # Update existing
            logger.info(
                "application_deduplicated", 
                app_id=str(existing_app.id), 
                new_status=event.event_type.value
            )
            # Only update status if it's a logical progression or different.
            # For simplicity, we just update to the new status and bump last_activity_at.
            # In a full system we'd check chronological ordering.
            existing_app.current_status = event.event_type
            existing_app.last_activity_at = event.event_date
            
            # Record history
            history = ApplicationStatusHistory(
                application_id=existing_app.id,
                user_id=user_id,
                status=event.event_type.value,
                source=StatusSource.EMAIL_IMPORT.value,
                detected_at=event.event_date,
                source_email_id=event.source_email_id,
                confidence_scores=event.confidence_scores.model_dump(),
            )
            session.add(history)
            
        else:
            # Create new
            logger.info(
                "application_created", 
                company=event.company, 
                role=event.role
            )
            new_app = Application(
                user_id=user_id,
                company_name=event.company,
                role_title=event.role,
                current_status=event.event_type,
                source_email_id=event.source_email_id,
                gmail_thread_id=event.gmail_thread_id,
                applied_at=event.event_date if event.event_type == ApplicationStatus.APPLIED else None,
                last_activity_at=event.event_date,
                confidence_scores=event.confidence_scores.model_dump(),
            )
            session.add(new_app)
            await session.flush() # flush to get new_app.id
            
            # Record history
            history = ApplicationStatusHistory(
                application_id=new_app.id,
                user_id=user_id,
                status=event.event_type.value,
                source=StatusSource.EMAIL_IMPORT.value,
                detected_at=event.event_date,
                source_email_id=event.source_email_id,
                confidence_scores=event.confidence_scores.model_dump(),
            )
            session.add(history)

    def _company_match(self, comp1: str, comp2: str) -> bool:
        """Helper for basic company string matching."""
        c1 = comp1.lower()
        c2 = comp2.lower()
        # E.g. "Google" in "Google LLC"
        return c1 in c2 or c2 in c1
        
    def _role_match(self, role1: str, role2: str) -> bool:
        """Helper for basic role string matching."""
        r1 = role1.lower()
        r2 = role2.lower()
        # Naive approach: check if one contains the other
        return r1 in r2 or r2 in r1


application_service = ApplicationService()
