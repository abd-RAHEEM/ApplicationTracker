"""Keyword classifier for status."""
from __future__ import annotations

import re
from app.models.application import ApplicationStatus


def classify_status(subject: str, body: str) -> tuple[ApplicationStatus, float]:
    """
    Determines the application status based on keyword scoring.
    """
    combined = f"{subject} {body}".lower()
    
    # Define keywords/phrases for each status
    status_keywords = {
        ApplicationStatus.REJECTED: [
            "unfortunately", "not moving forward", "other candidates", 
            "decided to pursue", "not be moving forward", "not selected"
        ],
        ApplicationStatus.OFFER: [
            "offer", "congratulations", "pleased to offer", "offer letter"
        ],
        ApplicationStatus.INTERVIEW: [
            "interview", "schedule", "zoom", "google meet", 
            "speak with", "chat with", "phone screen"
        ],
        ApplicationStatus.ASSESSMENT: [
            "hackerrank", "coderbyte", "assessment", "online test", 
            "take-home", "take home", "codesignal"
        ],
        ApplicationStatus.APPLIED: [
            "received your application", "thank you for applying", 
            "application received", "we have received"
        ]
    }
    
    # Count matches using word boundaries
    match_counts = {}
    for status, phrases in status_keywords.items():
        count = 0
        for phrase in phrases:
            # Escape the phrase and use word boundaries
            pattern = rf"\b{re.escape(phrase)}\b"
            if re.search(pattern, combined):
                count += 1
        match_counts[status] = count

    # Determine highest matching status
    best_status = ApplicationStatus.PENDING
    max_matches = 0
    
    # Prioritize ties: REJECTED > OFFER > INTERVIEW > ASSESSMENT > APPLIED
    priority_order = [
        ApplicationStatus.REJECTED,
        ApplicationStatus.OFFER,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.ASSESSMENT,
        ApplicationStatus.APPLIED
    ]
    
    for status in priority_order:
        count = match_counts[status]
        if count > max_matches:
            max_matches = count
            best_status = status

    # Calculate normalized confidence
    # min(1.0, matched_keyword_count / expected_threshold)
    if max_matches > 0:
        expected_threshold = 2.0
        confidence = min(1.0, max_matches / expected_threshold)
        # Ensure a minimum confidence for any match, e.g. 0.5
        confidence = max(0.5, confidence)
    else:
        confidence = 0.5
        
    return best_status, confidence
