"""Sender Domain Mapping."""
from __future__ import annotations

import re


def extract_company_from_sender(sender: str | None) -> tuple[str | None, float]:
    """
    Extracts company name from the sender's email address or display name.
    Returns (company_name, confidence).
    """
    if not sender:
        return None, 0.0

    # Look for generic ATS domains to ignore for company mapping
    ats_domains = [
        "greenhouse.io", "workday.com", "lever.co", "myworkday.com", 
        "breezy.hr", "icims.com", "ashbyhq.com", "smartrecruiters.com"
    ]
    
    # Try to parse "Company Name <email@domain.com>"
    match = re.search(r'(?:")?([^"<]+)(?:")?\s*<([^>]+)>', sender)
    if match:
        display_name = match.group(1).strip()
        email_addr = match.group(2).strip().lower()
    else:
        display_name = ""
        email_addr = sender.strip().lower()

    domain = email_addr.split('@')[-1] if '@' in email_addr else ""

    if domain and not any(ats in domain for ats in ats_domains):
        # E.g. careers@google.com -> "google", then capitalize -> "Google"
        company_domain = domain.split('.')[0]
        if company_domain.lower() not in ["gmail", "yahoo", "hotmail", "outlook"]:
            return company_domain.capitalize(), 0.9

    # If domain is an ATS, try to use the display name if it's descriptive
    if display_name and len(display_name) > 2 and "team" not in display_name.lower():
        # E.g. "Google Recruiting <no-reply@greenhouse.io>"
        cleaned_name = re.sub(r'(?i)\b(recruiting|careers|talent|team|hr|human resources)\b', '', display_name).strip()
        if cleaned_name:
            return cleaned_name, 0.8

    return None, 0.0
