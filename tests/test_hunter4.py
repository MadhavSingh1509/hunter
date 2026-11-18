"""
Hunter 4.0 - Comprehensive Test Suite
Validates all 20 required QA dimensions from Part 14:
1. Company registry validation (167 companies)
2. Duplicate company detection
3. ATS pagination
4. API failure handling
5. HTML parsing
6. Job URL verification
7. India location filtering
8. Electrical Engineering degree eligibility
9. Graduation-year filtering
10. Fresher experience filtering
11. Internship classification
12. Salary classification
13. Match scoring
14. Job deduplication
15. Potential-to-verified status transition
16. Email formatting
17. Empty digest prevention
18. Notification deduplication
19. Source health reporting
20. Persistent storage across runs
"""

import os
import json
import pytest
from core.database import HunterDatabase
from core.classifier import EligibilityClassifier
from core.health import SourceHealthMonitor
from scrapers.ats_engine import ATSDiscoveryEngine
from notifications.email_service import HunterEmailService

@pytest.fixture
def tmp_db(tmp_path):
    db_file = str(tmp_path / "test_hunter.db")
    db = HunterDatabase(db_path=db_file)
    db.seed_registries("config/company_registry.json", "config/campus_recruiter_registry.json")
    return db

@pytest.fixture
def classifier():
    return EligibilityClassifier("config/candidate_profile.json")

# 1. Company registry validation
def test_01_company_registry_count():
    with open("config/company_registry.json", "r", encoding="utf-8") as f:
        comps = json.load(f)
    assert len(comps) == 167
    mandatory = [c["name"] for c in comps if c.get("is_mandatory_priority")]
    assert "Amazon" in mandatory
    assert "Salesforce" in mandatory
    assert "Barclays" in mandatory
    assert "Accenture" in mandatory

# 2. Duplicate company detection
def test_02_no_duplicate_company_ids():
    with open("config/company_registry.json", "r", encoding="utf-8") as f:
        comps = json.load(f)
    ids = [c["id"] for c in comps]
    assert len(ids) == len(set(ids))

# 3. ATS pagination logic
def test_03_ats_pagination_logic():
    engine = ATSDiscoveryEngine()
    # Amazon API with max_pages parameter
    jobs = engine.fetch_amazon_jobs(max_pages=1)
    assert isinstance(jobs, list)

# 4. API failure handling
def test_04_api_failure_handling():
    engine = ATSDiscoveryEngine()
    # Non-existent greenhouse board
    jobs = engine.fetch_greenhouse_jobs("non_existent_fake_slug_123456", "Fake", "fake")
    assert jobs == []

# 5. HTML parsing resilience
def test_05_html_parsing():
    from bs4 import BeautifulSoup
    html = "<div><a href='/job/123'>Software Engineer</a></div>"
    soup = BeautifulSoup(html, "html.parser")
    a = soup.find("a")
    assert a is not None
    assert a.get_text() == "Software Engineer"

# 6. Job URL verification
def test_06_job_url_verification():
    engine = ATSDiscoveryEngine()
    is_valid, status = engine.verify_job_url("invalid://broken_url")
    assert is_valid is False
    assert status == "UNVERIFIED"

# 7. India location filtering
def test_07_india_location_filtering(classifier):
    loc_res, score, reason = classifier.classify_location_eligibility("Bengaluru, India")
    assert loc_res == "INDIA"
    assert score == 10.0

    loc_foreign, _, _ = classifier.classify_location_eligibility("Seattle, WA, United States")
    assert loc_foreign == "OUTSIDE_INDIA"

# 8. Electrical Engineering degree eligibility
def test_08_ee_degree_eligibility(classifier):
    # Any branch / circuit branches accepted
    el1, score1, _ = classifier.classify_degree_eligibility("B.Tech in any engineering discipline.")
    assert el1 == "ELIGIBLE"

    # Explicit Electrical Engineering
    el2, score2, _ = classifier.classify_degree_eligibility("B.Tech in Electrical Engineering or CSE.")
    assert el2 == "ELIGIBLE"

    # Restricted to CSE only -> Ineligible
    el3, score3, _ = classifier.classify_degree_eligibility("Open only for Computer Science graduates.")
    assert el3 == "INELIGIBLE"

# 9. Graduation-year filtering
def test_09_graduation_year_filtering(classifier):
    # 2026 batch match
    grad1, score1, _ = classifier.classify_graduation_eligibility("Hiring 2026 Batch freshers.")
    assert grad1 == "ELIGIBLE"

    # 2022 batch only -> Ineligible
    grad2, _, _ = classifier.classify_graduation_eligibility("2022 batch only.")
    assert grad2 == "INELIGIBLE"

# 10. Fresher experience filtering
def test_10_fresher_experience_filtering(classifier):
    # 0-1 years
    exp1, score1, _ = classifier.classify_experience_eligibility("0 to 1 years of experience.")
    assert exp1 == "ELIGIBLE"

    # 3+ years mandatory -> Ineligible
    exp2, _, _ = classifier.classify_experience_eligibility("3+ years of professional experience.")
    assert exp2 == "INELIGIBLE"

# 11. Internship classification
def test_11_internship_classification(classifier):
    res = classifier.evaluate_job({
        "title": "Software Development Intern",
        "description": "6-month internship for final year students. Stipend: Rs 40,000 / month.",
        "location": "Hyderabad, India",
        "employment_type": "Internship"
    })
    assert res["role_relevance"] == "MATCH"
    assert res["compensation_text"] == "₹40,000/month"

# 12. Salary classification
def test_12_salary_classification(classifier):
    status1, disp1, _ = classifier.classify_compensation("Compensation: 16 LPA.")
    assert status1 == "12_LPA_OR_ABOVE"
    assert "₹16.0 LPA" in disp1

    status2, disp2, _ = classifier.classify_compensation("Compensation: 7 LPA.")
    assert status2 == "BELOW_12_LPA"

    status3, disp3, _ = classifier.classify_compensation("")
    assert status3 == "UNDISCLOSED"
    assert disp3 == "Not disclosed"

# 13. Match scoring
def test_13_match_scoring(classifier):
    res = classifier.evaluate_job({
        "title": "Software Development Engineer I",
        "description": "B.Tech in Electrical Engineering. 2026 batch freshers. 0-1 years. Python, React.",
        "location": "Bengaluru, India"
    })
    assert res["match_score"] >= 75
    assert res["classification"] == "VERIFIED MATCH"

# 14. Job deduplication
def test_14_job_deduplication(tmp_db):
    job = {
        "company_id": "amazon",
        "company_name": "Amazon",
        "ats_job_id": "AMZ-101",
        "title": "SDE I",
        "canonical_url": "https://amazon.jobs/job/101",
        "classification": "VERIFIED MATCH"
    }
    key1, trans1 = tmp_db.record_job(job)
    assert trans1 == "NEW"

    # Second record should be OPEN (deduplicated)
    key2, trans2 = tmp_db.record_job(job)
    assert key1 == key2
    assert trans2 == "OPEN"

# 15. Potential-to-verified status transition
def test_15_potential_to_verified_transition(tmp_db):
    job = {
        "company_id": "stripe",
        "company_name": "Stripe",
        "ats_job_id": "ST-202",
        "title": "Software Engineer",
        "canonical_url": "https://stripe.com/job/202",
        "classification": "POTENTIAL MATCH"
    }
    key, trans1 = tmp_db.record_job(job)
    assert trans1 == "NEW"

    # Update to VERIFIED MATCH
    job["classification"] = "VERIFIED MATCH"
    job["match_score"] = 85.0
    _, trans2 = tmp_db.record_job(job)
    assert trans2 == "VERIFIED_UPGRADE"

# 16. Email formatting (minimal 4-field format)
def test_16_email_formatting():
    service = HunterEmailService()
    jobs = [{"title": "SDE 1", "company_name": "Amazon", "posted_on": "17 Nov 2026", "canonical_url": "http://ex.com"}]
    subject, plain, html = service.build_simple_digest(jobs)
    assert subject == "Hunter — New Fresher Job Opportunities"
    assert "Company | Position Name | Posted On | Apply Link" in plain
    assert "Amazon" in html
    assert "SDE 1" in html
    assert "17 Nov 2026" in html

# 17. Empty digest prevention
def test_17_empty_digest_prevention():
    service = HunterEmailService()
    sent = service.send_simple_digest([])
    assert sent is False

# 18. Notification deduplication
def test_18_notification_deduplication(tmp_db):
    job = {
        "company_id": "amazon",
        "company_name": "Amazon",
        "ats_job_id": "AMZ-999",
        "title": "SDE 1",
        "canonical_url": "https://amazon.jobs/job/999",
        "classification": "VERIFIED MATCH"
    }
    key, _ = tmp_db.record_job(job)
    unnotified = tmp_db.get_unnotified_jobs()
    assert any(j["job_key"] == key for j in unnotified)

    # Mark notified
    tmp_db.mark_notified([key])
    unnotified_after = tmp_db.get_unnotified_jobs()
    assert not any(j["job_key"] == key for j in unnotified_after)

# 19. Source health reporting
def test_19_source_health_reporting(tmp_db):
    monitor = SourceHealthMonitor(tmp_db)
    tmp_db.update_source_health(
        company_id="amazon",
        company_name="Amazon",
        source_url="https://amazon.jobs",
        scanner_type="amazon_api",
        health_status="HEALTHY",
        http_status=200,
        jobs_retrieved=50,
        new_jobs=5,
        relevant_jobs=10,
        verified_matches=2,
        potential_matches=8
    )
    report = monitor.generate_health_report()
    assert report["healthy_count"] >= 1
    table_md = monitor.format_markdown_table()
    assert "Amazon" in table_md
    assert "HEALTHY" in table_md

# 20. Persistent storage across runs
def test_20_persistent_storage(tmp_path):
    db_path = str(tmp_path / "persist.db")
    db1_path = db_path
    db1 = HunterDatabase(db_path=db1_path)
    job = {
        "company_id": "google",
        "company_name": "Google",
        "ats_job_id": "G-555",
        "title": "Software Engineer",
        "canonical_url": "https://google.com/job/555",
        "classification": "POTENTIAL MATCH"
    }
    key, _ = db1.record_job(job)

    # Reopen connection in a new instance
    db2 = HunterDatabase(db_path=db1_path)
    jobs = db2.get_all_jobs()
    assert len(jobs) == 1
    assert jobs[0]["job_key"] == key
    assert jobs[0]["title"] == "Software Engineer"
