"""Regex extraction rules."""
from __future__ import annotations

import re


def extract_role_via_regex(subject: str, body: str) -> tuple[str | None, float]:
    """
    Tries to extract the role/job title using common ATS phrasing.
    """
    combined = f"{subject} {body}"

    patterns = [
        # "Application for the position of Software Engineer at ..."
        r"(?i)application for (?:the )?(?:position of )?([A-Za-z0-9\s\-\/]+?)(?: at |$|\.)",
        # "Applying for the Software Engineer role ..."
        r"(?i)applying for (?:the )?([A-Za-z0-9\s\-\/]+?)(?: role| position| at|\.)",
        # "Regarding your application for the Software Engineer position ..."
        r"(?i)regarding your application for (?:the )?([A-Za-z0-9\s\-\/]+?)(?: position| role)",
        # "Thank you for applying to the Software Engineer position ..."
        r"(?i)thank you for applying (?:to )?(?:the )?([A-Za-z0-9\s\-\/]+?)(?: position| role| at|\.)",
        # "Thanks for applying for the Software Engineer ..."
        r"(?i)thanks for applying (?:for )?(?:the )?([A-Za-z0-9\s\-\/]+?)(?: position| role| at|\.)",
        # "Your application for Software Engineer has been ..."
        r"(?i)your application for (?:the )?([A-Za-z0-9\s\-\/]+?)(?: has been| at )",
        # "We received your application for Software Engineer ..."
        r"(?i)(?:we received|we've received|received) your application for (?:the )?([A-Za-z0-9\s\-\/]+?)(?: at | position| role|\.)",
        # "You applied for Software Engineer at ..."
        r"(?i)you applied for (?:the )?([A-Za-z0-9\s\-\/]+?)(?: at )",
        # "Interview for Software Engineer ..."
        r"(?i)interview for (?:the )?(?:role of |position of )?([A-Za-z0-9\s\-\/]+?)(?: at |$|\.)",
        # Subject line: "Re: Software Engineer - Application" or "Software Engineer | Application"
        r"(?i)^([A-Za-z0-9\s\-\/]+?)\s*[\|\-–—]\s*(?:application|interview|offer)",
    ]

    for pattern in patterns:
        match = re.search(pattern, combined)
        if match:
            role = match.group(1).strip()
            # Clean up trailing connector words
            role = re.sub(r'(?i)\b(at|role|position|the)\b.*', '', role).strip()
            role = re.sub(r'\s+', ' ', role).strip()
            if 3 < len(role) < 60:
                return role, 0.85

    return None, 0.0


def extract_company_via_regex(subject: str, body: str) -> tuple[str | None, float]:
    """
    Tries to extract the company using common ATS phrasing.
    """
    combined = f"{subject} {body}"

    patterns = [
        # "Thank you for applying to [Company]"
        r"(?i)thank you for applying (?:to )?(?:[A-Za-z0-9\s\-\/]+? at )?([A-Za-z0-9\s\.\,\&]+?)(?:\.|!|\n|$)",
        # "Application for [Role] at [Company]"
        r"(?i)application for [A-Za-z0-9\s\-\/]+? at ([A-Za-z0-9\s\.\&]+?)(?:\.|!|\n|$)",
        # "Your application to [Company]"
        r"(?i)your application to ([A-Za-z0-9\s\.\&]+?)(?:\.|!|\n|$)",
        # "Interview with [Company]"
        r"(?i)interview with ([A-Za-z0-9\s\.\&]+?)(?:\.|!|\n|$)",
        # "at [Company]'s recruiting ..." — possessive
        r"(?i)\bat ([A-Za-z0-9\s]+?)(?:'s)?\s+(?:recruiting|team|careers)",
        # "from the [Company] team"
        r"(?i)from (?:the )?([A-Za-z0-9\s\.\&]+?) (?:team|recruiting|talent)",
        # "on behalf of [Company]"
        r"(?i)on behalf of ([A-Za-z0-9\s\.\&]+?)(?:\.|,|\n|$)",
        # "join [Company]"
        r"(?i)join (?:the )?([A-Za-z0-9\s\.\&]+?) (?:team|family)",
        # "[Company] is excited to ..."
        r"(?i)^([A-Za-z0-9\s\.\&]+?) (?:is|are) (?:excited|pleased|happy|delighted) to",
    ]

    for pattern in patterns:
        match = re.search(pattern, combined)
        if match:
            company = match.group(1).strip()
            company = re.sub(r'\s+', ' ', company).strip()
            # Reject if too short, too long, or a generic word
            generic_words = {"the", "our", "your", "this", "that", "we", "i", "a", "an"}
            if len(company) > 1 and len(company) < 40 and company.lower() not in generic_words:
                return company, 0.85

    return None, 0.0
