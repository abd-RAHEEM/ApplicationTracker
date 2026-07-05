"""Pre-filter to determine if an email is job-related without fetching the full body."""
from __future__ import annotations

import re


def is_job_related(subject: str | None, sender: str | None, snippet: str | None) -> bool:
    """
    Quickly filters out obvious non-job emails using subject, sender, and snippet.

    Strategy: err on the side of inclusion — it is cheaper to fetch the full body
    of a false-positive and discard it in the parser than to silently drop a real
    job email at this stage.  Only hard-spam signals trigger early rejection.
    """
    subject_str = (subject or "").lower()
    sender_str  = (sender  or "").lower()
    snippet_str = (snippet or "").lower()
    combined    = f"{subject_str} {snippet_str}"

    # ── Always pass ATS / recruiting senders ────────────────────────────────
    ats_sender_signals = [
        "careers@", "recruiting@", "talent@", "ats@", "noreply@",
        "no-reply@", "jobs@", "greenhouse.io", "lever.co", "workday.com",
        "myworkday.com", "icims.com", "smartrecruiters.com", "ashbyhq.com",
        "taleo.net", "successfactors.com", "jobvite.com", "breezy.hr",
        "recruitee.com", "comeet.co",
    ]
    if any(sig in sender_str for sig in ats_sender_signals):
        return True

    # ── Hard-spam signals — definite non-job email ───────────────────────────
    # Only exclude if there are spam signals AND zero job signals in combined text
    spam_keywords = [
        "newsletter", "promotions", "flash sale", "discount", "coupon",
        "order confirmation", "shipping update", "invoice", "payment received",
        "subscription renewal", "account statement", "bank statement",
        "password reset", "verify your email", "confirm your email",
        "unsubscribe", "opt out",
    ]
    spam_score = sum(1 for k in spam_keywords if k in combined)

    # ── Job-relevance signals ────────────────────────────────────────────────
    job_keywords = [
        "application", "apply", "applied", "candidate", "interview", "assessment",
        "offer", "resume", "cv", "portfolio", "moving forward", "next steps",
        "unfortunately", "hackerrank", "coderbyte", "codesignal", "talent",
        "recruiter", "careers", "job", "position", "role", "opportunity",
        "hiring", "onboarding", "job offer", "offer letter", "phone screen",
    ]
    job_score = sum(1 for k in job_keywords if re.search(rf"\b{re.escape(k)}\b", combined))

    # If there are any job signals, pass even if some spam signals are present
    if job_score > 0:
        return True

    # No job signals + spam signals → reject
    if spam_score > 0:
        return False

    # No clear signal either way: be permissive, let the parser decide
    return True
