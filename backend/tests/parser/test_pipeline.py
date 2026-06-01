import pytest
from app.core.parser.domain_mapping import extract_company_from_sender
from app.core.parser.email_classifier import classify_email_type
from app.core.parser.keyword_classifier import classify_status
from app.schemas.parser import EmailType
from app.models.application import ApplicationStatus

@pytest.mark.asyncio
async def test_email_classification():
    # Newsletter
    t1 = classify_email_type("Weekly Digest", "Glassdoor", "Here are top companies")
    assert t1 == EmailType.NEWSLETTER
    
    # Job Alert
    t2 = classify_email_type("30 new jobs for you", "LinkedIn", "Matches your profile")
    assert t2 == EmailType.JOB_ALERT
    
    # Application Event
    t3 = classify_email_type("Thank you for applying", "Google", "We have received your application")
    assert t3 == EmailType.APPLICATION_EVENT
    
def test_domain_mapping():
    # ATS stripping
    company, conf = extract_company_from_sender("OpenAI Recruiting <no-reply@greenhouse.io>")
    assert company == "OpenAI"
    assert conf == 0.8
    
    # Normal domain
    company, conf = extract_company_from_sender("Recruiting <careers@stripe.com>")
    assert company == "stripe"
    assert conf == 0.9
    
def test_status_classification():
    # Interview
    status, conf = classify_status("Interview with Netflix", "We would like to schedule a call")
    assert status == ApplicationStatus.INTERVIEW
    
    # Offer
    status, conf = classify_status("Offer Letter", "We are thrilled to offer you...")
    assert status == ApplicationStatus.OFFER
    
    # Rejected
    status, conf = classify_status("Update on your application", "Unfortunately we will not be moving forward")
    assert status == ApplicationStatus.REJECTED
