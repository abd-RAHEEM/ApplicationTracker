"""Keyword classifier for status."""
from __future__ import annotations

import re
from app.models.application import ApplicationStatus


def classify_status(subject: str, body: str) -> tuple[ApplicationStatus, float]:
    """
    Determines the application status based on keyword scoring.
    """
    combined = f"{subject} {body}".lower()
    
    # Keyword sets and their weights
    scores = {
        ApplicationStatus.REJECTED: 0,
        ApplicationStatus.OFFER: 0,
        ApplicationStatus.INTERVIEW: 0,
        ApplicationStatus.ASSESSMENT: 0,
        ApplicationStatus.APPLIED: 0,
    }
    
    # Rejection is usually explicit and final
    if re.search(r'\b(unfortunately|not moving forward|other candidates|decided to pursue|not be moving forward|not selected)\b', combined):
        scores[ApplicationStatus.REJECTED] += 10
        
    # Offer
    if re.search(r'\b(offer|congratulations|pleased to offer|offer letter)\b', combined):
        scores[ApplicationStatus.OFFER] += 8
        
    # Interview
    if re.search(r'\b(interview|schedule|zoom|google meet|speak with|chat with|phone screen)\b', combined):
        scores[ApplicationStatus.INTERVIEW] += 6
        
    # Assessment
    if re.search(r'\b(hackerrank|coderbyte|assessment|online test|take-home|take home|codesignal)\b', combined):
        scores[ApplicationStatus.ASSESSMENT] += 6
        
    # Applied
    if re.search(r'\b(received your application|thank you for applying|application received|we have received)\b', combined):
        scores[ApplicationStatus.APPLIED] += 4
        
    # Find the highest score
    best_status = ApplicationStatus.PENDING
    best_score = 0
    
    for status, score in scores.items():
        if score > best_score:
            best_score = score
            best_status = status
            
    # Calculate confidence based on how decisive the score is
    confidence = 0.5
    if best_score >= 10:
        confidence = 0.95
    elif best_score >= 6:
        confidence = 0.85
    elif best_score >= 4:
        confidence = 0.75
        
    return best_status, confidence
