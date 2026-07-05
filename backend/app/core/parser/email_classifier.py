"""Email type classification."""
from __future__ import annotations

import re

from app.schemas.parser import EmailType


def classify_email_type(subject: str, sender: str, body: str) -> EmailType:
    """
    Classifies the email into APPLICATION_EVENT, JOB_ALERT, NEWSLETTER, or OTHER.

    Broad APPLICATION_EVENT detection: any email that appears to be from/about
    a specific job application at a specific company. We intentionally cast a
    wider net here and rely on the downstream parser to confirm company/role
    extraction — better to over-include than silently drop legitimate emails.
    """
    combined = f"{subject} {sender} {body[:2000]}".lower()
    subject_lower = subject.lower()
    sender_lower = sender.lower()

    # ── Newsletters / mass-marketing (hard exclude) ──────────────────────────
    if re.search(
        r'\b(newsletter|weekly digest|monthly update|unsubscribe from this list'
        r'|this email was sent to you because you subscribed)\b',
        combined,
    ):
        return EmailType.NEWSLETTER

    # ── Job alert / recommendation digests ──────────────────────────────────
    if re.search(
        r'\b(job alert|recommended jobs|new jobs for you|jobs matching your'
        r'|daily jobs|weekly jobs|job recommendations|top jobs this week)\b',
        combined,
    ):
        return EmailType.JOB_ALERT

    # ── Explicit APPLICATION_EVENT phrases (high-confidence) ────────────────
    high_confidence_patterns = [
        # Confirmations
        r'\b(thank you for applying|thanks for applying|application received'
        r'|we have received your application|your application has been received'
        r'|successfully submitted your application|application submitted)\b',
        # Status updates
        r'\b(regarding your application|update on your application'
        r'|application status|your application for|we reviewed your application'
        r'|after careful consideration|after reviewing your application)\b',
        # Rejections
        r'\b(unfortunately|we will not be moving forward|not moving forward'
        r'|decided to pursue other candidates|not be proceeding|other candidates'
        r'|not selected|not a match at this time|position has been filled)\b',
        # Interviews / next steps
        r'\b(interview with|schedule an interview|invite you to interview'
        r'|phone screen|technical interview|on-site interview|virtual interview'
        r'|moving forward with your application|next steps in your application)\b',
        # Offers
        r'\b(offer letter|pleased to extend|we are delighted to offer'
        r'|formal offer|offer of employment|offer of position)\b',
        # Assessments
        r'\b(complete an assessment|take-home assignment|coding challenge'
        r'|hackerrank|codesignal|coderbyte|technical assessment|online test)\b',
    ]
    if any(re.search(p, combined) for p in high_confidence_patterns):
        return EmailType.APPLICATION_EVENT

    # ── Sender-based signals (ATS / recruiting domains) ─────────────────────
    # Emails from known ATS systems are almost certainly application events
    ats_sender_patterns = [
        r'@greenhouse\.io\b', r'@lever\.co\b', r'@workday\.com\b',
        r'@myworkday\.com\b', r'@icims\.com\b', r'@smartrecruiters\.com\b',
        r'@ashbyhq\.com\b', r'@breezy\.hr\b', r'@taleo\.net\b',
        r'@successfactors\.com\b', r'@jobvite\.com\b', r'@recruitee\.com\b',
        r'@comeet\.co\b', r'@pinpoint\.com\b', r'@rippling\.com\b',
        r'careers@', r'recruiting@', r'talent@', r'noreply@.*recruit',
        r'no-reply@.*recruit', r'jobs@',
    ]
    if any(re.search(p, sender_lower) for p in ats_sender_patterns):
        return EmailType.APPLICATION_EVENT

    # ── Subject-line heuristics ──────────────────────────────────────────────
    subject_patterns = [
        r'\bapplication\b',
        r'\binterview\b',
        r'\bopportunity\b.*\b(role|position)\b',
        r'\byour candidacy\b',
        r'\bwe\'d like to\b',
        r'\bexcited to share\b',
    ]
    if any(re.search(p, subject_lower) for p in subject_patterns):
        return EmailType.APPLICATION_EVENT

    return EmailType.OTHER
