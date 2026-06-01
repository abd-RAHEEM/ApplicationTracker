import asyncio
from datetime import datetime

from app.core.parser.domain_mapping import extract_company_from_sender
from app.core.parser.regex_rules import extract_company_via_regex
from app.services.parser_service import parser_service


def test_extraction():
    test_cases = [
        {
            "name": "Greenhouse",
            "sender": "OpenAI Recruiting <no-reply@greenhouse.io>",
            "subject": "Thank you for applying to the Software Engineer role",
            "body": "Thank you for applying to OpenAI! We will review your application."
        },
        {
            "name": "Lever",
            "sender": "Netflix Careers <applicant@lever.co>",
            "subject": "Application for Data Scientist at Netflix",
            "body": "We have received your application to Netflix."
        },
        {
            "name": "Workday",
            "sender": "Amazon <no-reply@myworkday.com>",
            "subject": "Interview with Amazon",
            "body": "We would like to invite you for a zoom interview."
        },
        {
            "name": "Ashby",
            "sender": "Stripe Talent <no-reply@ashbyhq.com>",
            "subject": "Moving forward",
            "body": "We are excited to move forward with your application."
        },
        {
            "name": "SmartRecruiters",
            "sender": "Square Recruiting <noreply@smartrecruiters.com>",
            "subject": "Not moving forward",
            "body": "Unfortunately, we decided to pursue other candidates."
        },
        {
            "name": "LinkedIn Job Alert",
            "sender": "LinkedIn <jobalerts@linkedin.com>",
            "subject": "30 new jobs matching your profile",
            "body": "Here are some new jobs for you."
        },
        {
            "name": "Glassdoor Newsletter",
            "sender": "Glassdoor <noreply@glassdoor.com>",
            "subject": "Weekly digest: top companies to work for",
            "body": "Check out this week's newsletter."
        }
    ]
    
    print("--- ATS Company Extraction Verification ---")
    for tc in test_cases:
        event = parser_service.parse_email(
            msg_id="test",
            thread_id="thread",
            subject=tc["subject"],
            sender=tc["sender"],
            date=datetime.now(),
            body=tc["body"]
        )
        if event:
            print(f"[{tc['name']}]")
            print(f"  Sender: {tc['sender']}")
            print(f"  Email Type: {event.email_type.value}")
            print(f"  Company: {event.company} (conf: {event.confidence_scores.company})")
            print(f"  Role: {event.role} (conf: {event.confidence_scores.role})")
            print(f"  Status: {event.event_type.value} (conf: {event.confidence_scores.status})")
            print("-" * 40)


if __name__ == "__main__":
    test_cases = test_extraction()
