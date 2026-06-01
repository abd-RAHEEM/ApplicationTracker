"""Regex extraction rules."""
from __future__ import annotations

import re


def extract_role_via_regex(subject: str, body: str) -> tuple[str | None, float]:
    """
    Tries to extract the role/job title using common ATS phrasing.
    """
    combined = f"{subject} {body}"
    
    patterns = [
        r"(?i)application for (?:the )?(?:position of )?([A-Za-z0-9\s\-]+?)(?: at |$|\.)",
        r"(?i)applying for (?:the )?([A-Za-z0-9\s\-]+?)(?: role| position| at|\.)",
        r"(?i)regarding your application for (?:the )?([A-Za-z0-9\s\-]+?)(?: position| role)",
        r"(?i)thank you for applying to (?:the )?([A-Za-z0-9\s\-]+?)(?: position| role)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, combined)
        if match:
            role = match.group(1).strip()
            # Clean up trailing words that might get caught
            role = re.sub(r'(?i)\b(at|role|position)\b.*', '', role).strip()
            if len(role) > 3 and len(role) < 50:
                return role, 0.85
                
    return None, 0.0


def extract_company_via_regex(subject: str, body: str) -> tuple[str | None, float]:
    """
    Tries to extract the company using common ATS phrasing.
    """
    combined = f"{subject} {body}"
    
    patterns = [
        r"(?i)thank you for applying to (?:the )?[A-Za-z0-9\s\-]+? at ([A-Za-z0-9\s]+?)(?:\.|!|$)",
        r"(?i)application for [A-Za-z0-9\s\-]+? at ([A-Za-z0-9\s]+?)(?:\.|!|$)",
        r"(?i)your application to ([A-Za-z0-9\s]+?)(?:\.|!|$)",
        r"(?i)interview with ([A-Za-z0-9\s]+?)(?:\.|!|$)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, combined)
        if match:
            company = match.group(1).strip()
            if len(company) > 1 and len(company) < 30:
                return company, 0.85
                
    return None, 0.0
