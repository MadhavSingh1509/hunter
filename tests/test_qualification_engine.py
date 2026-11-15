"""
Hunter 2.0 Comprehensive Test Suite
Validates the multi-stage qualification engine, strict rejection gates,
authenticity verifier, and scoring across 36 representative real-world test cases.
"""

import pytest
from qualification_engine import (
    QualificationEngine, JobPosting, QualificationResult,
    REJECT_EXPERIENCE, REJECT_DEGREE_BRANCH, REJECT_GRAD_YEAR,
    REJECT_LOCATION, REJECT_SENIORITY_ROLE, REJECT_CLOSED, REJECT_AUTH
)
from authenticity_verifier import AuthenticityVerifier, CLOSED_PAGE_INDICATORS
from config import load_candidate_profile


@pytest.fixture
def engine():
    profile = load_candidate_profile()
    # Ensure standard candidate configuration for deterministic testing
    profile["candidate"]["degree"] = "B.Tech"
    profile["candidate"]["branch"] = "Electrical Engineering"
    profile["candidate"]["graduation_year"] = 2026
    profile["candidate"]["eligible_graduation_years"] = [2026]
    profile["candidate"]["experience_years_max"] = 0
    profile["candidate"]["has_professional_software_experience"] = False
    return QualificationEngine(profile)


# 1. SDE, 0 years, any B.Tech branch -> VERIFIED MATCH
def test_01_sde_0_years_any_btech(engine):
    job = JobPosting(
        company="Amazon",
        title="Software Development Engineer I",
        location="Bangalore, Karnataka, India",
        description="Freshers welcome. B.Tech/B.E. in any engineering discipline. 0 years experience required. Skills: DSA, C++, Java.",
        url="https://amazon.jobs/en/jobs/12345"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75
    assert not res.rejection_reasons


# 2. Software Engineer, 0–1 years, any engineering branch -> VERIFIED MATCH
def test_02_software_engineer_0_to_1_yrs_any_eng(engine):
    job = JobPosting(
        company="Cisco",
        title="Software Engineer",
        location="Bangalore, India",
        description="Looking for 0-1 years of experience. Education: Bachelor's degree in engineering or equivalent technical field. Python, REST APIs.",
        url="https://jobs.cisco.com/jobs/67890"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 3. Software Engineer, 2+ years mandatory -> REJECT
def test_03_software_engineer_2_plus_years(engine):
    job = JobPosting(
        company="Razorpay",
        title="Software Engineer",
        location="Bangalore, India",
        description="Requirements: Minimum 2+ years of software engineering experience required. Strong Node.js.",
        url="https://razorpay.com/jobs/111"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_EXPERIENCE in r for r in res.rejection_reasons)


# 4. Senior Software Engineer, 4 years -> REJECT
def test_04_senior_software_engineer_4_years(engine):
    job = JobPosting(
        company="Flipkart",
        title="Senior Software Engineer - Backend",
        location="Bangalore, India",
        description="4+ years of backend development experience. High scale distributed systems.",
        url="https://flipkart.com/jobs/222"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_SENIORITY_ROLE in r for r in res.rejection_reasons)


# 5. Graduate Engineer Trainee, Electrical Engineering accepted -> VERIFIED MATCH
def test_05_get_electrical_accepted(engine):
    job = JobPosting(
        company="L&T Technology Services",
        title="Graduate Engineer Trainee - Software Development",
        location="Pune, India",
        description="Freshers welcome. Open to B.Tech Electrical Engineering, Electronics, and IT. Software track training in C++ and Python.",
        url="https://ltts.com/careers/get-101"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 6. Graduate Engineer Trainee, CSE only -> REJECT
def test_06_get_cse_only(engine):
    job = JobPosting(
        company="TCS",
        title="Graduate Engineer Trainee - IT",
        location="Hyderabad, India",
        description="Eligibility: Strictly CSE/IT candidates only. B.Tech in Computer Science only. Other branches not eligible.",
        url="https://tcs.com/careers/get-cse"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_DEGREE_BRANCH in r for r in res.rejection_reasons)


# 7. SDE Intern, final-year students accepted -> VERIFIED MATCH
def test_07_sde_intern_final_year(engine):
    job = JobPosting(
        company="Swiggy",
        title="Software Development Intern",
        location="Bangalore, India",
        description="Internship for final year students. B.Tech any branch. Problem solving, Data Structures, Algorithms.",
        url="https://swiggy.com/careers/intern-1"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 8. Internship restricted to 2027 graduates -> REJECT
def test_08_internship_2027_only(engine):
    job = JobPosting(
        company="Google",
        title="Software Engineering Intern, Summer 2027",
        location="Hyderabad, India",
        description="Eligibility: Currently enrolled in Bachelor's program with graduation in 2027 batch only.",
        url="https://careers.google.com/jobs/intern-2027"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_GRAD_YEAR in r for r in res.rejection_reasons)


# 9. Job restricted to 2025 graduates -> REJECT
def test_09_job_restricted_to_2025(engine):
    job = JobPosting(
        company="Infosys",
        title="Associate Software Engineer",
        location="Pune, India",
        description="Eligibility: Restricted to 2025 passout batch only. Immediate joiners.",
        url="https://infosys.com/jobs/2025"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_GRAD_YEAR in r for r in res.rejection_reasons)


# 10. Software Engineer, 0 years, but requiring Master's degree -> REJECT
def test_10_swe_requires_masters(engine):
    job = JobPosting(
        company="Microsoft Research",
        title="Software Engineer - AI Systems",
        location="Bangalore, India",
        description="0 years experience. Requirements: Mandatory Master's degree in Engineering or Ph.D required.",
        url="https://careers.microsoft.com/jobs/msr-1"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_DEGREE_BRANCH in r for r in res.rejection_reasons)


# 11. Job with no disclosed experience requirements -> UNCERTAIN / POTENTIAL MATCH
def test_11_no_disclosed_experience(engine):
    job = JobPosting(
        company="Groww",
        title="Software Engineer",
        location="Bangalore, India",
        description="Build scalable microservices with React and Node.js. Fast-paced startup environment.",
        url="https://groww.in/careers/swe"
    )
    res = engine.evaluate(job)
    assert res.verdict == "POTENTIAL MATCH"
    assert any("Experience requirement not disclosed" in u for u in res.uncertain_flags)


# 12. Expired job listing -> REJECT
def test_12_expired_job_listing(engine):
    job = JobPosting(
        company="CRED",
        title="Backend Developer",
        location="Bangalore, India",
        description="0-1 years. Python, Node.js.",
        url="https://cred.club/careers/closed-1",
        is_active=False
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_CLOSED in r for r in res.rejection_reasons)


# 13. Broken application link verification test
def test_13_broken_application_link():
    verifier = AuthenticityVerifier()
    # Bad URL without scheme or non-existent domain
    is_valid, reason, _ = verifier.verify_application_url("https://this-is-a-completely-fake-domain-12345.com/apply")
    assert is_valid is False
    assert "network error" in reason.lower() or "not found" in reason.lower()


# 14. Accessible official ATS application page verification test
def test_14_accessible_official_ats():
    verifier = AuthenticityVerifier()
    assert verifier.is_known_ats_platform("https://boards.greenhouse.io/postman/jobs/12345") is True
    assert verifier.is_known_ats_platform("https://jobs.lever.co/paytm/67890") is True


# 15. Job requiring mandatory 3+ years experience despite fresher-friendly title
def test_15_associate_swe_requiring_3_years(engine):
    job = JobPosting(
        company="Oracle",
        title="Associate Software Engineer",
        location="Hyderabad, India",
        description="Qualifications: 3+ years of professional industry software experience required.",
        url="https://oracle.com/jobs/ase-3yr"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_EXPERIENCE in r for r in res.rejection_reasons)


# 16. Electrical core role (Substation design engineer) -> REJECT
def test_16_core_electrical_substation(engine):
    job = JobPosting(
        company="ABB",
        title="Electrical Site Engineer (Substation & Transformers)",
        location="Vadodara, India",
        description="Substation wiring, transformer maintenance, high voltage switchgear testing.",
        url="https://abb.com/jobs/substation"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_SENIORITY_ROLE in r for r in res.rejection_reasons)


# 17. SDE at US location (Seattle, USA) -> REJECT
def test_17_us_location(engine):
    job = JobPosting(
        company="Amazon US",
        title="Software Development Engineer I",
        location="Seattle, WA, USA",
        description="0-1 years. Any engineering branch.",
        url="https://amazon.jobs/en/jobs/seattle-1"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_LOCATION in r for r in res.rejection_reasons)


# 18. Remote India full-stack developer, 0-1 yr -> VERIFIED MATCH
def test_18_remote_india_fullstack(engine):
    job = JobPosting(
        company="Postman",
        title="Full Stack Developer",
        location="Remote - India",
        description="0-1 years. Bachelor's in engineering or equivalent. React, Node.js, Express, REST APIs.",
        url="https://boards.greenhouse.io/postman/jobs/fsd"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 19. SDE-1 explicitly listing "B.Tech in Electrical / Electronics / CSE" -> VERIFIED MATCH
def test_19_btech_ee_explicit(engine):
    job = JobPosting(
        company="Qualcomm",
        title="Software Engineer I",
        location="Hyderabad, India",
        description="0 years experience. Eligibility: B.Tech in Electrical Engineering, Electronics, or Computer Science. C++, Data Structures.",
        url="https://qualcomm.com/jobs/ee-swe"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 80


# 20. Software Engineer requiring active US security clearance -> REJECT
def test_20_security_clearance_required(engine):
    job = JobPosting(
        company="DefenseTech",
        title="Software Engineer",
        location="Bangalore, India",
        description="0-1 years. Active US Security Clearance required. US citizenship required.",
        url="https://defense.com/jobs/clearance"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_AUTH in r for r in res.rejection_reasons)


# 21. GET Core Transformer Manufacturing (No software) -> REJECT
def test_21_get_core_manufacturing(engine):
    job = JobPosting(
        company="Siemens Energy",
        title="Graduate Engineer Trainee - Plant Operations",
        location="Mumbai, India",
        description="Responsible for high voltage transformer assembly and factory maintenance.",
        url="https://siemens.com/jobs/get-factory"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_SENIORITY_ROLE in r for r in res.rejection_reasons)


# 22. Frontend Developer (React, JS), freshers welcome -> VERIFIED MATCH
def test_22_frontend_developer_fresher(engine):
    job = JobPosting(
        company="Meesho",
        title="Frontend Developer",
        location="Bangalore, India",
        description="Freshers welcome. 0 years experience. Any B.Tech branch. React.js, JavaScript, HTML, CSS.",
        url="https://meesho.com/jobs/fe-fresh"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 23. Backend Developer (Python, REST APIs), 0-1 yrs -> VERIFIED MATCH
def test_23_backend_developer_python(engine):
    job = JobPosting(
        company="Chargebee",
        title="Backend Developer",
        location="Chennai, India",
        description="0-1 years experience. B.Tech all engineering branches. Python, REST APIs, MongoDB, SQL.",
        url="https://chargebee.com/jobs/be-py"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 24. Borderline 0 to 2 years -> POTENTIAL MATCH
def test_24_borderline_0_to_2_years(engine):
    job = JobPosting(
        company="Innovaccer",
        title="Software Engineer",
        location="Noida, India",
        description="0-2 years experience required. All engineering disciplines eligible. Java, SQL.",
        url="https://innovaccer.com/jobs/swe-0-2"
    )
    res = engine.evaluate(job)
    assert res.verdict == "POTENTIAL MATCH"
    assert any("0-2 years" in u for u in res.uncertain_flags)


# 25. Technical Sales Executive -> REJECT
def test_25_sales_executive_tech(engine):
    job = JobPosting(
        company="Dell",
        title="Technical Sales Executive",
        location="Gurgaon, India",
        description="B.Tech freshers welcome. Cold calling, lead qualification, software sales targets.",
        url="https://dell.com/jobs/sales"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_SENIORITY_ROLE in r for r in res.rejection_reasons)


# 26. Technical Recruiter / HR -> REJECT
def test_26_hr_recruiter_tech(engine):
    job = JobPosting(
        company="Urban Company",
        title="Technical Recruiter - Engineering Hiring",
        location="Gurgaon, India",
        description="Hiring software engineers and developers. 0-1 years.",
        url="https://urbancompany.com/jobs/recruiter"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_SENIORITY_ROLE in r for r in res.rejection_reasons)


# 27. Principal Software Architect, 10+ years -> REJECT
def test_27_lead_architect_10_years(engine):
    job = JobPosting(
        company="Adobe",
        title="Principal Software Architect",
        location="Noida, India",
        description="10+ years of distributed architecture design experience.",
        url="https://adobe.com/jobs/arch"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_SENIORITY_ROLE in r for r in res.rejection_reasons)


# 28. Internship strictly for 2nd year students -> REJECT
def test_28_internship_second_year_only(engine):
    job = JobPosting(
        company="Uber",
        title="Software Engineering Intern",
        location="Hyderabad, India",
        description="Open strictly to 2nd year students only. Pre-final year program.",
        url="https://uber.com/jobs/intern-2nd"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_GRAD_YEAR in r for r in res.rejection_reasons)


# 29. SDE I for 2026 Batch Graduates -> VERIFIED MATCH
def test_29_sde1_batch_2026(engine):
    job = JobPosting(
        company="Arista Networks",
        title="Software Engineer I",
        location="Bangalore, India",
        description="2026 passout batch. Open to B.Tech Electrical Engineering and Computer Science. C++, Data Structures, Linux.",
        url="https://arista.com/jobs/2026-swe"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 85


# 30. QA Automation Engineer, freshers eligible -> VERIFIED MATCH
def test_30_qa_automation_fresher(engine):
    job = JobPosting(
        company="BrowserStack",
        title="QA Automation Engineer",
        location="Mumbai, India",
        description="0-1 years. Any B.Tech degree. Test automation with Python, Java, and SQL.",
        url="https://browserstack.com/jobs/qa-auto"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 31. Application Developer, Bangalore, 0 years -> VERIFIED MATCH
def test_31_application_developer_bangalore(engine):
    job = JobPosting(
        company="Thoughtworks",
        title="Application Developer",
        location="Bangalore, India",
        description="Freshers welcome. 0 years. All engineering branches eligible. Java, Python, React.",
        url="https://thoughtworks.com/jobs/app-dev"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 32. Junior Web Developer, MERN stack, 0 yrs -> VERIFIED MATCH
def test_32_junior_web_developer_mern(engine):
    job = JobPosting(
        company="Zomato",
        title="Junior Software Developer",
        location="Gurgaon, India",
        description="0 years. B.Tech in any branch. MERN stack: MongoDB, Express.js, React.js, Node.js.",
        url="https://zomato.com/jobs/jr-dev"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 80


# 33. "Required: 0-1 years. Preferred: 2 years" -> VERIFIED MATCH (not rejected, because 2 yrs is preferred)
def test_33_preferred_vs_mandatory_experience(engine):
    job = JobPosting(
        company="Paytm",
        title="Software Engineer",
        location="Noida, India",
        description="Required: 0-1 years experience. Preferred: 2 years experience in React. Bachelor's in engineering or equivalent.",
        url="https://jobs.lever.co/paytm/swe-pref"
    )
    res = engine.evaluate(job)
    assert res.verdict == "VERIFIED MATCH"
    assert res.score >= 75


# 34. Job requires mandatory 2+ years of professional industry software experience -> REJECT
def test_34_project_exp_not_industry_exp(engine):
    job = JobPosting(
        company="Nutanix",
        title="Software Development Engineer",
        location="Bangalore, India",
        description="Candidate must have 2+ years of professional software work experience. Personal projects do not count.",
        url="https://nutanix.com/jobs/sde-prof"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_EXPERIENCE in r for r in res.rejection_reasons)


# 35. Software Engineering Intern, "Remote - US Only" -> REJECT
def test_35_remote_us_internship(engine):
    job = JobPosting(
        company="Stripe",
        title="Software Engineering Intern",
        location="Remote - US Only",
        description="0 years. Summer internship.",
        url="https://boards.greenhouse.io/stripe/jobs/us-intern"
    )
    res = engine.evaluate(job)
    assert res.verdict == "REJECTED"
    assert any(REJECT_LOCATION in r for r in res.rejection_reasons)


# 36. Closed listing indicator detection
def test_36_closed_listing_page_detection():
    import re
    snippet = "Thank you for your interest. This position is no longer accepting applications."
    matched = any(re.search(p, snippet.lower()) for p in CLOSED_PAGE_INDICATORS)
    assert matched is True


# 37. Pipeline modules import sanity test
def test_37_pipeline_modules_import():
    import monitor
    import ats_providers
    import email_sender
    import application_tracker
    import config
    import tracker
    assert hasattr(monitor, "run_pipeline")

