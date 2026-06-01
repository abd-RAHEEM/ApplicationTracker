"""Parser orchestration service."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.core.parser.domain_mapping import extract_company_from_sender
from app.core.parser.email_classifier import classify_email_type
from app.core.parser.keyword_classifier import classify_status
from app.core.parser.regex_rules import extract_company_via_regex, extract_role_via_regex
from app.core.parser.spacy_ner import extract_entities_via_spacy
from app.schemas.parser import ConfidenceScores, EmailType, NormalizedEvent

logger = structlog.get_logger(__name__)


class ParserService:
    """Orchestrates the parsing pipeline for a single email."""

    def parse_email(
        self,
        msg_id: str,
        thread_id: str,
        subject: str | None,
        sender: str | None,
        date: datetime | None,
        body: str | None,
    ) -> NormalizedEvent | None:
        """
        Runs the full deterministic parsing pipeline.
        Returns a NormalizedEvent if job-related entities are found, else None.
        """
        subject_str = subject or ""
        body_str = body or ""
        
        # 0. Classify Email Type
        email_type = classify_email_type(subject_str, sender or "", body_str)
        
        # 1. Classify Status
        status, status_conf = classify_status(subject_str, body_str)
        
        # 2. Extract Company
        company = None
        company_conf = 0.0
        
        # 2a. Try domain mapping first
        comp, conf = extract_company_from_sender(sender)
        if comp and conf > company_conf:
            company, company_conf = comp, conf
            
        # 2b. Try regex if not confident
        if company_conf < 0.8:
            comp, conf = extract_company_via_regex(subject_str, body_str)
            if comp and conf > company_conf:
                company, company_conf = comp, conf
                
        # 2c. Try spaCy as last resort
        if company_conf < 0.6:
            comp, conf = extract_entities_via_spacy(subject_str, body_str)
            if comp and conf > company_conf:
                company, company_conf = comp, conf
                
        # 3. Extract Role
        role = None
        role_conf = 0.0
        
        rl, r_conf = extract_role_via_regex(subject_str, body_str)
        if rl and r_conf > role_conf:
            role, role_conf = rl, r_conf
            
        # If we couldn't find a company OR a role, we consider it unparsable/unrelated
        if not company and not role:
            return None
            
        # Fill in defaults if partially matched
        if not company:
            company = "Unknown Company"
        if not role:
            role = "Unknown Role"

        return NormalizedEvent(
            company=company,
            role=role,
            event_type=status,
            email_type=email_type,
            event_date=date or datetime.now(),
            source_email_id=msg_id,
            gmail_thread_id=thread_id,
            confidence_scores=ConfidenceScores(
                company=company_conf,
                role=role_conf,
                status=status_conf,
            )
        )

    async def process_unparsed_emails(self, session: AsyncSession, user_id: UUID) -> None:
        """
        Retrieves unparsed emails, applies job-relevance filter,
        fetches full bodies from Gmail API if needed, and passes them to the Application Engine.
        """
        from sqlalchemy import select
        from app.models.email import Email
        from app.core.parser.pre_filter import is_job_related
        from app.services.application_service import application_service
        from app.core.gmail_client import GmailClient
        from app.repositories.gmail_repository import gmail_repository

        # Get Gmail connection
        conn = await gmail_repository.get_connection(session, user_id)
        if not conn:
            return

        client = GmailClient(conn.encrypted_refresh_token)

        try:
            # Query unparsed emails
            result = await session.execute(
                select(Email)
                .where(Email.user_id == user_id, Email.is_parsed == False)
                .order_by(Email.gmail_internal_date.asc())
            )
            unparsed_emails = result.scalars().all()

            for email in unparsed_emails:
                email.parse_attempts += 1
                try:
                    # Pre-filter
                    if is_job_related(email.subject, email.sender, email.snippet):
                        # Temporarily fetch full body
                        body = await client.fetch_full_body(email.gmail_msg_id)
                        
                        event = self.parse_email(
                            msg_id=email.gmail_msg_id,
                            thread_id=email.gmail_thread_id,
                            subject=email.subject,
                            sender=email.sender,
                            date=email.date,
                            body=body
                        )
                        
                        if event and event.email_type == EmailType.APPLICATION_EVENT:
                            await application_service.process_normalized_event(session, user_id, event)
                    
                    email.is_parsed = True
                    email.parsed_at = datetime.now()
                    email.last_parse_error = None
                    await session.commit() # commit after each successful email parsing

                except Exception as e:
                    logger.exception("email_parsing_error", msg_id=email.gmail_msg_id)
                    email.last_parse_error = str(e)
                    await session.commit()
        finally:
            await client.close()

parser_service = ParserService()
