"""spaCy NER and heuristic fallback for entity extraction."""
from __future__ import annotations

import re
import structlog

logger = structlog.get_logger(__name__)

# Lazy load spaCy to avoid huge startup memory consumption if not called
nlp = None


def _get_nlp():
    global nlp
    if nlp is None:
        try:
            import spacy
            # Load ONLY the "ner" component. This disables:
            # - tok2vec
            # - tagger
            # - parser
            # - attribute_ruler
            # - lemmatizer
            # This reduces spaCy's RAM footprint from ~250MB down to ~35-50MB.
            nlp = spacy.load(
                "en_core_web_sm",
                disable=["tok2vec", "tagger", "parser", "attribute_ruler", "lemmatizer"],
            )
            logger.info("spacy_loaded_with_minimal_components")
        except Exception as e:
            logger.error("spacy_load_failed_falling_back_to_heuristics", error=str(e))
            nlp = False
    return nlp


# Heuristic Suffixes & Regexes (Fallback/Verification)
_CORP_SUFFIXES = re.compile(
    r"\b(Inc\.?|LLC\.?|Ltd\.?|Corp\.?|Co\.?|GmbH|S\.A\.|PLC|AG|NV|BV|"
    r"Technologies|Technology|Solutions|Services|Systems|Software|"
    r"Consulting|Group|Holdings|Ventures|Labs|Studio|Studios|Media|"
    r"Capital|Partners|Associates|Enterprises|International|Global|"
    r"Digital|Analytics|Networks|Platform|Platforms|Cloud)\b",
    re.IGNORECASE,
)

_TITLE_CASE_RUN = re.compile(
    r"\b([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3})\b"
)

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
    Extracts the company name from email text.
    Uses spaCy NER (optimized) if available, falling back to a clean regex heuristic.
    """
    combined = f"{subject} {body[:1500]}"
    
    # 1. Try spaCy NLP first (if available and loaded)
    model = _get_nlp()
    if model:
        try:
            doc = model(combined)
            orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            if orgs:
                # Find most common ORG
                from collections import Counter
                most_common, _ = Counter(orgs).most_common(1)[0]
                
                # Sanitize it
                clean_org = re.sub(r'(?i)\b(Inc\.|LLC|Ltd\.|Corporation)\b', '', most_common).strip()
                if _is_valid_company(clean_org):
                    return clean_org, 0.65
        except Exception as e:
            logger.error("spacy_ner_runtime_failed", error=str(e))

    # 2. Heuristic Fallback (Regex-based)
    # Pass 1: Look for a Title-Case run within proximity of a corporate suffix
    for suffix_match in _CORP_SUFFIXES.finditer(combined):
        start = max(0, suffix_match.start() - 60)
        snippet = combined[start:suffix_match.end() + 20]
        for tc in _TITLE_CASE_RUN.finditer(snippet):
            candidate = tc.group(1).strip()
            full = f"{candidate} {suffix_match.group(0).strip()}".strip()
            full = re.sub(r"\s+", " ", full)
            if _is_valid_company(full):
                return full, 0.55

    # Pass 2: Two-or-more consecutive Title-Case words not in stopwords
    for tc in _TITLE_CASE_RUN.finditer(combined):
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
    if not name[0].isupper():
        return False
    if name in _STOPWORDS:
        return False
    return True
