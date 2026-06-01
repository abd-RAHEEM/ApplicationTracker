"""Pre-filter to determine if an email is job-related without fetching the full body."""
from __future__ import annotations

import re


def is_job_related(subject: str | None, sender: str | None, snippet: str | None) -> bool:
    """
    Analyzes metadata and snippet to quickly filter out obvious non-job emails.
    """
    subject = (subject or "").lower()
    sender = (sender or "").lower()
    snippet = (snippet or "").lower()
    
    combined_text = f"{subject} {snippet}"
    
    # Common job application keywords
    job_keywords = [
        "application", "apply", "candidate", "interview", "assessment", 
        "offer", "resume", "portfolio", "moving forward", "next steps",
        "unfortunately", "hackerrank", "coderbyte", "talent", "recruiter",
        "careers", "jobs"
    ]
    
    # Common non-job keywords
    spam_keywords = [
        "newsletter", "promotions", "sale", "discount", "order", "receipt",
        "shipping", "invoice", "payment", "subscription"
    ]
    
    if any(k in sender for k in ["careers@", "jobs@", "talent@", "recruiting@", "ats@"]):
        return True
        
    job_score = sum(1 for k in job_keywords if k in combined_text)
    spam_score = sum(1 for k in spam_keywords if k in combined_text)
    
    if spam_score > job_score:
        return False
        
    return job_score > 0
