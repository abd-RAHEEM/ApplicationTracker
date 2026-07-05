"""
Lightweight company name extraction — spaCy-free fallback.

Replaces spaCy NER with a zero-dependency regex heuristic that identifies
organisation-like tokens using structural patterns (Title Case runs, known
corporate suffixes, capitalisation cues).

Memory footprint: ~0 MB (no model loading).
Accuracy: lower than spaCy but good enough as a last-resort fallback after
domain_mapping and regex_rules have already had a first pass.
"""
from __future__ import annotations

import re


# Common corporate / legal suffixes that indicate a word is part of a company name
_CORP_SUFFIXES = re.compile(
    r"\b(Inc\.?|LLC\.?|Ltd\.?|Corp\.?|Co\.?|GmbH|S\.A\.|PLC|AG|NV|BV|"
    r"Technologies|Technology|Solutions|Services|Systems|Software|"
    r"Consulting|Group|Holdings|Ventures|Labs|Studio|Studios|Media|"
    r"Capital|Partners|Associates|Enterprises|International|Global|"
    r"Digital|Analytics|Networks|Platform|Platforms|Cloud)\b",
    re.IGNORECASE,
)

# Words that look like company names: 2-4 consecutive Title-Cased tokens
# not starting with common English words.
_TITLE_CASE_RUN = re.compile(
    r"\b([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3})\b"
)

# Common non-company title-case words to filter out
_STOPWORDS = {
    "Dear", "Hi", "Hello", "Thank", "Thanks", "We", "Our", "Your",
    "The", "This", "That", "Please", "See", "Let", "We're", "You're",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "New", "Next", "Last", "Best", "Great", "Good", "Job",
    "Application", "Position", "Role", "Interview", "Offer", "Team",
    "Human", "Resources", "Recruiting", "Talent", "Acquisition",
    "Re", "From", "To", "Subject", "Email", "Message",
}


def extract_entities_via_spacy(subject: str, body: str) -> tuple[str | None, float]:
    """
    Lightweight drop-in replacement for the spaCy NER extractor.

    Strategy:
    1. Scan for Title-Case word runs near corporate suffix words.
    2. Fall back to any Title-Case run that is ≥2 words and not a stopword.

    Returns (company_name, confidence) where confidence ≤ 0.55 (lower than
    domain_mapping and regex_rules so it never overrides them).
    """
    # Only look at the subject + first 1000 chars of body to stay fast
    text = f"{subject} {body[:1000]}"

    # Pass 1: Look for a Title-Case run within 5 words of a corporate suffix
    for suffix_match in _CORP_SUFFIXES.finditer(text):
        start = max(0, suffix_match.start() - 60)
        snippet = text[start:suffix_match.end() + 20]
        for tc in _TITLE_CASE_RUN.finditer(snippet):
            candidate = tc.group(1).strip()
            # Include the suffix itself if it's right after the candidate
            full = f"{candidate} {suffix_match.group(0).strip()}".strip()
            full = re.sub(r"\s+", " ", full)
            if _is_valid_company(full):
                return full, 0.55

    # Pass 2: Two-or-more consecutive Title-Case words not in stopwords
    for tc in _TITLE_CASE_RUN.finditer(text):
        candidate = tc.group(1).strip()
        words = candidate.split()
        if len(words) >= 2 and not any(w in _STOPWORDS for w in words):
            if _is_valid_company(candidate):
                return candidate, 0.45

    return None, 0.0


def _is_valid_company(name: str) -> bool:
    """Basic sanity check on a candidate company name."""
    name = name.strip()
    if len(name) < 2 or len(name) > 50:
        return False
    # Must start with a capital letter
    if not name[0].isupper():
        return False
    # Reject if it's a single generic stopword
    if name in _STOPWORDS:
        return False
    return True
