"""
Hunter — Comprehensive Test Suite for the Simple Fresher Job Filter Upgrade
Verifies all requirements from Sections 1–10:
- Watchlist integrity (71 existing companies, zero added, all configured)
- Strict fresher filtering (accepts genuine fresher/intern/new-grad; rejects experienced & ambiguous)
- Amazon '1+ years of non-internship experience' trap rejection
- B.Tech Electrical Engineering branch eligibility & CSE-only rejection
- 2027 Graduation year compatibility
- Strict India-only location filtering
- Posting date normalization & 'Not disclosed' fallback (no fabrication)
- Official application URL validation (rejects generic careers homepages)
- Simple 4-field email format (exact Subject + ONLY Company | Position Name | Posted On | Apply Link)
- Empty email prevention & duplicate notification prevention
"""

import json
import pytest
from core.fresher_filter import StrictFresherFilter
from core.database import HunterDatabase
from scrapers.portal_scanner import format_posted_date, PortalScanner
from notifications.email_service import HunterEmailService, SIMPLE_EMAIL_SUBJECT


@pytest.fixture
def flt():
    return StrictFresherFilter(graduation_year=2027)


def test_watchlist_has_exact_71_companies_with_scanners():
    with open("companies.json", "r", encoding="utf-8") as f:
        comps = json.load(f)
    assert len(comps) == 71
    names = [c["name"] for c in comps]
    assert len(names) == len(set(names))
    for c in comps:
        assert "scanner" in c and "type" in c["scanner"]


def test_accepts_genuine_fresher_and_intern_roles(flt):
    # 1. Software Engineer Intern in Bengaluru
    d1 = flt.evaluate(
        "Software Engineer, Intern",
        "Bengaluru, India",
        "Currently pursuing a B.Tech degree in Engineering. Strong DSA and coding skills."
    )
    assert d1.is_eligible is True

    # 2. University Graduate SDE I (0-1 years, any branch)
    d2 = flt.evaluate(
        "Software Development Engineer I",
        "Hyderabad, India",
        "Entry level role for fresh graduates. 0-1 years experience. B.Tech in any engineering branch."
    )
    assert d2.is_eligible is True

    # 3. AI/ML Intern in Pune
    d3 = flt.evaluate(
        "AI/ML Intern",
        "Pune, India",
        "Internship opportunity for 2027 batch B.Tech students in Python and Machine Learning."
    )
    assert d3.is_eligible is True

    # 4. 0-2 years when fresh graduates are eligible
    d4 = flt.evaluate(
        "Associate Software Engineer",
        "Mumbai, India",
        "0-2 years of experience. Fresh graduates welcome. B.Tech Electrical or Computer Science."
    )
    assert d4.is_eligible is True


def test_rejects_amazon_non_internship_trap(flt):
    # Classic Amazon SDE JD that previously bypassed because 'non-internship' matched 'internship'
    d = flt.evaluate(
        "Software Development Engineer, Amazon Business India",
        "Bengaluru, IND",
        "Basic Qualifications: 1+ years of non-internship professional software development experience. "
        "Bachelor's degree in Computer Science or related field."
    )
    assert d.is_eligible is False
    assert "non-internship" in d.reason.lower()


def test_rejects_cisco_phd_zero_years_and_title_years_trap(flt):
    # Exact Cisco pattern discovered during live validation
    d1 = flt.evaluate(
        "Software Engineer :: C/C++, Python scripting, L2/L3 Networking (5-9 Years)",
        "Bangalore, India",
        "Bachelor's degree + 5 years of related experience, OR Master's degree + 3 years of related experience, OR Ph.D. + 0 years of related experience."
    )
    assert d1.is_eligible is False

    d2 = flt.evaluate(
        "Software Engineer",
        "Bangalore, India",
        "Minimum Qualifications: Bachelor's degree + 3 years of related experience, OR Master's degree + 1 year of related experience, OR Ph.D. + 0 years of related experience."
    )
    assert d2.is_eligible is False

    # Genuine Cisco 0-1 / 0-2 years Bachelor's fresher role MUST still pass!
    d3 = flt.evaluate(
        "Software Engineer",
        "Bangalore, India",
        "Minimum Qualifications: Bachelor's degree in Computer Science, Electrical Engineering or related field. 0-1 years of related experience."
    )
    assert d3.is_eligible is True


def test_rejects_experienced_and_senior_roles(flt):
    assert flt.evaluate("Senior Software Engineer", "Bengaluru, India", "Freshers welcome").is_eligible is False
    assert flt.evaluate("Software Development Engineer II", "Hyderabad, India", "0-1 years").is_eligible is False
    assert flt.evaluate("Staff AI Engineer", "Bengaluru, India", "Entry level").is_eligible is False
    assert flt.evaluate("Lead Backend Engineer", "Pune, India", "0 years").is_eligible is False
    assert flt.evaluate(
        "Software Engineer",
        "Bengaluru, India",
        "Minimum 3 years of professional software development experience required."
    ).is_eligible is False
    assert flt.evaluate(
        "Associate Software Engineer",
        "Noida, India",
        "Requires 2-4 years of industry experience in Java."
    ).is_eligible is False


def test_rejects_ambiguous_roles_without_fresher_confirmation(flt):
    # "Do not assume a job is for freshers merely because its title says Associate, Graduate or Engineer.
    # If the job's fresher eligibility cannot be established, do not include it in my email."
    d1 = flt.evaluate(
        "Software Engineer",
        "Bengaluru, India",
        "Build scalable distributed backend services using Java, Go, and Kubernetes."
    )
    assert d1.is_eligible is False

    d2 = flt.evaluate(
        "Associate Software Engineer",
        "Pune, India",
        "Work with cross-functional teams to deliver enterprise cloud applications."
    )
    assert d2.is_eligible is False


def test_electrical_engineering_eligibility(flt):
    # Accepts Electrical Engineering / all branches
    assert flt.evaluate(
        "Graduate Software Engineer",
        "Chennai, India",
        "Entry level graduate program open to all engineering branches including Electrical Engineering."
    ).is_eligible is True

    # Rejects CSE/IT-only
    d_cs_only = flt.evaluate(
        "Graduate Software Engineer",
        "Bengaluru, India",
        "Freshers hiring. Open strictly for Computer Science and IT graduates only."
    )
    assert d_cs_only.is_eligible is False

    # Rejects PhD-only / Master's-only
    assert flt.evaluate(
        "PhD Machine Learning Engineer, Intern",
        "Bengaluru, India",
        "Currently pursuing a PhD in Machine Learning."
    ).is_eligible is False


def test_graduation_year_2027_filter(flt):
    assert flt.evaluate(
        "Software Engineer Intern",
        "Bengaluru, India",
        "Open to B.Tech students graduating in 2027."
    ).is_eligible is True

    d_old = flt.evaluate(
        "Software Engineer - New Grad",
        "Hyderabad, India",
        "Strictly for 2024 batch graduates only."
    )
    assert d_old.is_eligible is False


def test_india_only_location_filter(flt):
    assert flt.evaluate("Software Engineer Intern", "Bengaluru", "B.Tech student").is_eligible is True
    assert flt.evaluate("Software Engineer Intern", "Remote - India", "B.Tech student").is_eligible is True
    assert flt.evaluate("Software Engineer Intern", "United States", "B.Tech student").is_eligible is False
    assert flt.evaluate("Software Engineer Intern - Warsaw 2027", "Warsaw, Poland", "B.Tech student").is_eligible is False
    assert flt.evaluate("Software Engineer Intern", "Remote", "Work from anywhere in North America").is_eligible is False


def test_posting_date_formatting():
    assert format_posted_date("2026-11-17T10:30:00Z") == "17 Nov 2026"
    assert format_posted_date("November 16, 2026") == "16 Nov 2026"
    assert format_posted_date(None) == "Not disclosed"
    assert format_posted_date("") == "Not disclosed"
    assert format_posted_date("Posted 30+ Days Ago") == "30+ days ago"


def test_url_verification_rejects_generic_careers_homepage(flt):
    scanner = PortalScanner(flt)
    assert scanner.verify_application_url("https://www.company.com/careers") is False
    assert scanner.verify_application_url("https://www.company.com/jobs") is False
    assert scanner.verify_application_url("not-a-url") is False


def test_simple_4_field_email_format_only():
    jobs = [
        {
            "company_name": "Amazon",
            "title": "Software Development Engineer Intern",
            "posted_on": "17 Nov 2026",
            "canonical_url": "https://www.amazon.jobs/en/jobs/12345/sde-intern",
        },
        {
            "company_name": "Stripe",
            "title": "Software Engineer, Intern",
            "posted_on": "Not disclosed",
            "canonical_url": "https://stripe.com/jobs/search?gh_jid=8031833",
        },
    ]
    subject, plain, html_body = HunterEmailService.build_simple_digest(jobs)

    assert subject == "Hunter — New Fresher Job Opportunities"
    assert subject == SIMPLE_EMAIL_SUBJECT

    # Verify exact 4 columns in plain text
    lines = plain.splitlines()
    assert lines[0] == "Company | Position Name | Posted On | Apply Link"
    assert lines[1] == "Amazon | Software Development Engineer Intern | 17 Nov 2026 | https://www.amazon.jobs/en/jobs/12345/sde-intern"
    assert lines[2] == "Stripe | Software Engineer, Intern | Not disclosed | https://stripe.com/jobs/search?gh_jid=8031833"

    # Verify forbidden clutter is NOT present in HTML or plain text
    for forbidden in ["Match Score", "Score:", "LPA", "Compensation", "Dashboard", "SECTION 1", "Potential Matches", "Scanned:"]:
        assert forbidden not in html_body
        assert forbidden not in plain

    # Empty digest prevention
    assert HunterEmailService().send_simple_digest([]) is False


def test_duplicate_prevention_across_runs(tmp_path):
    db = HunterDatabase(db_path=str(tmp_path / "dedup.db"))
    job = {
        "company_id": "stripe",
        "company_name": "Stripe",
        "ats_job_id": "8031833",
        "title": "Software Engineer, Intern",
        "canonical_url": "https://stripe.com/jobs/search?gh_jid=8031833",
        "posted_on": "17 Nov 2026",
        "classification": "VERIFIED MATCH",
    }
    key1, t1 = db.record_job(job)
    assert t1 == "NEW"
    assert len(db.get_unnotified_verified_jobs()) == 1

    db.mark_notified([key1])
    assert len(db.get_unnotified_verified_jobs()) == 0

    # Same unchanged job discovered in next 12-hour scan -> NOT re-emailed
    key2, t2 = db.record_job(job)
    assert key1 == key2
    assert t2 == "OPEN"
    assert len(db.get_unnotified_verified_jobs()) == 0
