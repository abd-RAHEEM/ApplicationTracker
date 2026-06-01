"""Email type classification."""
from __future__ import annotations

import re

from app.schemas.parser import EmailType


def classify_email_type(subject: str, sender: str, body: str) -> EmailType:
    """
    Classifies the email into APPLICATION_EVENT, JOB_ALERT, NEWSLETTER, or OTHER.
    """
    combined = f"{subject} {sender} {body[:500]}".lower()
    
    # Check for newsletters first
    if re.search(r'\b(newsletter|weekly digest|monthly update|subscriber|unsubscribe from this list)\b', combined):
        return EmailType.NEWSLETTER
        
    # Check for job alerts / recommendations
    if re.search(r'\b(job alert|recommended jobs|new jobs for you|jobs matching your|daily jobs|weekly jobs|job recommendations)\b', combined):
        return EmailType.JOB_ALERT
        
    # Check for explicit application events
    # If the email addresses a specific application, interview, or offer
    app_patterns = [
        r'\b(thank you for applying|application for|regarding your application|moving forward|interview with|offer letter|unfortunately|not moving forward)\b'
    ]
    if any(re.search(p, combined) for p in app_patterns):
        return EmailType.APPLICATION_EVENT
        
    return EmailType.OTHER
