"""Keyword classifier for status."""
from __future__ import annotations

import re
from app.models.application import ApplicationStatus


def classify_status(subject: str, body: str) -> tuple[ApplicationStatus, float]:
    """
    Determines the application status based on keyword scoring.

    We intentionally use a broad set of real-world ATS phrasings.  Status
    priority (for ties): REJECTED > OFFER > INTERVIEW > ASSESSMENT > APPLIED.
    """
    combined = f"{subject} {body}".lower()

    status_keywords = {
        ApplicationStatus.REJECTED: [
            "unfortunately",
            "not moving forward",
            "will not be moving forward",
            "we will not be proceeding",
            "decided not to move forward",
            "other candidates",
            "decided to pursue",
            "not be moving forward",
            "not selected",
            "not a match",
            "position has been filled",
            "we have decided to move in a different direction",
            "chosen to move forward with other",
            "we regret to inform",
            "after careful consideration",   # often precedes rejection
        ],
        ApplicationStatus.OFFER: [
            "offer",
            "congratulations",
            "pleased to offer",
            "offer letter",
            "formal offer",
            "offer of employment",
            "we are excited to offer",
            "delighted to offer",
        ],
        ApplicationStatus.INTERVIEW: [
            "interview",
            "schedule",
            "zoom",
            "google meet",
            "microsoft teams",
            "speak with",
            "chat with",
            "phone screen",
            "phone call",
            "video call",
            "meeting request",
            "we'd like to connect",
            "we would love to connect",
            "invite you to",
            "next steps",
        ],
        ApplicationStatus.ASSESSMENT: [
            "hackerrank",
            "coderbyte",
            "assessment",
            "online test",
            "take-home",
            "take home",
            "codesignal",
            "coding challenge",
            "technical test",
            "skills test",
            "complete the following",
            "technical exercise",
        ],
        ApplicationStatus.APPLIED: [
            "received your application",
            "thank you for applying",
            "thanks for applying",
            "application received",
            "we have received",
            "we've received",
            "successfully applied",
            "application submitted",
            "we've got your application",
            "your application is under review",
            "application is being reviewed",
        ],
    }

    # Count phrase matches using word boundaries
    match_counts: dict[ApplicationStatus, int] = {}
    for status, phrases in status_keywords.items():
        count = 0
        for phrase in phrases:
            pattern = rf"\b{re.escape(phrase)}\b"
            if re.search(pattern, combined):
                count += 1
        match_counts[status] = count

    # Determine highest-scoring status
    best_status = ApplicationStatus.PENDING
    max_matches = 0

    priority_order = [
        ApplicationStatus.REJECTED,
        ApplicationStatus.OFFER,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.ASSESSMENT,
        ApplicationStatus.APPLIED,
    ]

    for status in priority_order:
        count = match_counts[status]
        if count > max_matches:
            max_matches = count
            best_status = status

    # Normalized confidence
    if max_matches > 0:
        expected_threshold = 2.0
        confidence = min(1.0, max_matches / expected_threshold)
        confidence = max(0.5, confidence)
    else:
        confidence = 0.5

    return best_status, confidence
