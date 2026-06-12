"""spaCy NER for fallback entity extraction."""
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

class DummyDoc:
    def __init__(self) -> None:
        self.ents = []


class DummySpacy:
    def __init__(self) -> None:
        self.failed = True

    def __call__(self, text: str) -> DummyDoc:
        return DummyDoc()


# Lazy load spaCy to avoid huge startup times if it's not needed immediately
nlp = None

def _get_nlp():
    global nlp
    if nlp is None:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.error("spacy_load_failed", error=str(e))
            # Create a dummy callable to prevent repeated failures crashing
            nlp = DummySpacy()
    return nlp


def extract_entities_via_spacy(subject: str, body: str) -> tuple[str | None, float]:
    """
    Extracts the most prominent ORG from the text.
    """
    model = _get_nlp()
    if getattr(model, "failed", False):
        return None, 0.0
        
    # We only process the first 2000 chars to save CPU time since
    # company names are usually at the top/bottom.
    combined = f"{subject} {body[:2000]}"
    
    try:
        doc = model(combined)
        orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        
        if not orgs:
            return None, 0.0
            
        # Very naive: just take the most common ORG or the first one
        from collections import Counter
        most_common_org, count = Counter(orgs).most_common(1)[0]
        
        # Strip common legal suffixes
        import re
        clean_org = re.sub(r'(?i)\b(Inc\.|LLC|Ltd\.|Corporation)\b', '', most_common_org).strip()
        
        if len(clean_org) > 1 and len(clean_org) < 50:
            return clean_org, 0.6 # Low confidence because NER can be noisy
            
    except Exception as e:
        logger.error("spacy_extraction_failed", error=str(e))
        
    return None, 0.0
