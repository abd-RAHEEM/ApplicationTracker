"""Schemas for the parsing pipeline."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.application import ApplicationStatus


class EmailType(str, Enum):
    APPLICATION_EVENT = "APPLICATION_EVENT"
    JOB_ALERT = "JOB_ALERT"
    NEWSLETTER = "NEWSLETTER"
    OTHER = "OTHER"


class ConfidenceScores(BaseModel):
    """Confidence levels for each extracted entity."""
    company: float = Field(0.0, ge=0.0, le=1.0)
    role: float = Field(0.0, ge=0.0, le=1.0)
    status: float = Field(0.0, ge=0.0, le=1.0)


class NormalizedEvent(BaseModel):
    """A standardized event extracted from an email."""
    company: str
    role: str
    event_type: ApplicationStatus
    email_type: EmailType
    event_date: datetime
    source_email_id: str
    gmail_thread_id: str
    confidence_scores: ConfidenceScores
