"""
HUNTER 4.0 — Automated India-Based Fresher SDE & AI/ML Job Discovery System
Main orchestrator for:
- Registry management (167 companies & 57 campus recruiters)
- Multi-source ATS discovery (Amazon, Salesforce, Barclays, Accenture, Greenhouse, Lever, SmartRecruiters, Ashby)
- 7-Dimension eligibility classification (B.Tech Electrical Engineering, 2026 Batch, 0 yrs exp)
- 100-Point scoring system with hard rejection gates
- Persistent SQLite storage & state transition tracking (data/hunter.db)
- Source health diagnostics (HEALTHY, DEGRADED, FAILED, NOT_CONFIGURED)
- 4-Section responsive email notification digest
- Synchronized CSV & JSON exports (applications.csv, job_tracker.json)
"""

import os
import sys
import json
import time
import logging
from typing import List, Dict, Any, Tuple, Optional

# Core & Service Imports
from core.database import HunterDatabase
from core.classifier import EligibilityClassifier
from core.health import SourceHealthMonitor
from scrapers.ats_engine import ATSDiscoveryEngine
from notifications.email_service import HunterEmailService

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("hunter")

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
COMPANY_REGISTRY_PATH = os.path.join(CONFIG_DIR, "company_registry.json")
CAMPUS_REGISTRY_PATH = os.path.join(CONFIG_DIR, "campus_recruiter_registry.json")
CANDIDATE_PROFILE_PATH = os.path.join(CONFIG_DIR, "candidate_profile.json")

def run_hunter():
    start_time = time.time()
    print("=" * 75)
    print("🎯 HUNTER 4.0 — AUTOMATED FRESHER SDE & AI/ML JOB DISCOVERY SYSTEM")
    print("=" * 75)

    # 1. Initialize Database & Seed Registries
    db = HunterDatabase()
    db.seed_registries(COMPANY_REGISTRY_PATH, CAMPUS_REGISTRY_PATH)
    classifier = EligibilityClassifier(CANDIDATE_PROFILE_PATH)
    ats_engine = ATSDiscoveryEngine(timeout=12)
    email_service = HunterEmailService()
    health_monitor = SourceHealthMonitor(db)

    # Print Candidate Profile Summary
    candidate = classifier.candidate
    print(f"👤 Candidate: {candidate.get('name')} | Degree: {candidate.get('degree')} {candidate.get('branch')}")
    print(f"🎓 Graduation Batch: {candidate.get('graduation_year')} | Max Experience: {candidate.get('experience_years_max')} years (Fresher)")
    print(f"📍 Preferred Locations: India Only | Target Compensation: >= 12 LPA (Undisclosed accepted)")
    print("=" * 75)

    # Load Companies from Registry
    with open(COMPANY_REGISTRY_PATH, "r", encoding="utf-8") as f:
        companies = json.load(f)

    # Sort companies: mandatory priority first, then high priority, then normal
    companies.sort(key=lambda c: (not c.get("is_mandatory_priority", False), c.get("priority") != "high", c["name"]))

    total_companies_scanned = 0
    total_jobs_retrieved = 0
    total_new_discovered = 0
    total_verified_matches = 0
    total_potential_matches = 0

    print(f"\n[DISCOVERY] Beginning scan across {len(companies)} registered employers...\n")

    for idx, comp in enumerate(companies, 1):
        comp_id = comp["id"]
        comp_name = comp["name"]
        ats_type = comp.get("ats_type", "custom")
        ats_id = comp.get("ats_identifier", "")
        is_mandatory = comp.get("is_mandatory_priority", False)

        retrieved_jobs: List[Dict[str, Any]] = []
        health_status = "HEALTHY"
        http_code = 200
        error_msg = None

        try:
            # Dispatch to appropriate scraper adapter
            if ats_type == "amazon_api":
                retrieved_jobs = ats_engine.fetch_amazon_jobs(max_pages=2)
            elif ats_type == "salesforce_workday":
                retrieved_jobs = ats_engine.fetch_salesforce_jobs(max_pages=2)
            elif ats_type == "barclays_talentbrew":
                retrieved_jobs = ats_engine.fetch_barclays_jobs(max_pages=2)
            elif ats_type == "accenture_api":
                retrieved_jobs = ats_engine.fetch_accenture_jobs()
            elif ats_type == "greenhouse" and ats_id:
                retrieved_jobs = ats_engine.fetch_greenhouse_jobs(ats_id, comp_name, comp_id)
            elif ats_type == "lever" and ats_id:
                retrieved_jobs = ats_engine.fetch_lever_jobs(ats_id, comp_name, comp_id)
            elif ats_type == "smartrecruiters" and ats_id:
                retrieved_jobs = ats_engine.fetch_smartrecruiters_jobs(ats_id, comp_name, comp_id)
            elif ats_type == "ashby" and ats_id:
                retrieved_jobs = ats_engine.fetch_ashby_jobs(ats_id, comp_name, comp_id)
            else:
                health_status = "NOT_CONFIGURED"

            if health_status != "NOT_CONFIGURED":
                total_companies_scanned += 1
                total_jobs_retrieved += len(retrieved_jobs)

        except Exception as e:
            health_status = "FAILED"
            http_code = 500
            error_msg = str(e)
            logger.error(f"[{comp_name}] Scanner failed: {e}")

        # Evaluate and record jobs
        comp_relevant_count = 0
        comp_verified_count = 0
        comp_potential_count = 0
        comp_new_count = 0

        for raw_job in retrieved_jobs:
            eval_result = classifier.evaluate_job(raw_job)

            # Skip rejected roles from cluttering notifications, but record statistics
            if eval_result["classification"] == "REJECTED":
                continue

            comp_relevant_count += 1
            if eval_result["classification"] == "VERIFIED MATCH":
                comp_verified_count += 1
                total_verified_matches += 1
            else:
                comp_potential_count += 1
                total_potential_matches += 1

            # Combine job data
            merged_job = {**raw_job, **eval_result}
            job_key, transition = db.record_job(merged_job)

            if transition == "NEW":
                comp_new_count += 1
                total_new_discovered += 1
                prefix = "★ [NEW VERIFIED]" if eval_result["classification"] == "VERIFIED MATCH" else "• [NEW POTENTIAL]"
                print(f"  {prefix} {comp_name} — {raw_job['title']} (Score: {eval_result['match_score']}/100)")
            elif transition == "VERIFIED_UPGRADE":
                print(f"  ▲ [UPGRADE] {comp_name} — {raw_job['title']} upgraded to VERIFIED MATCH")

        # Record source health
        if health_status != "NOT_CONFIGURED":
            db.update_source_health(
                company_id=comp_id,
                company_name=comp_name,
                source_url=comp.get("careers_url", ""),
                scanner_type=ats_type,
                health_status=health_status,
                http_status=http_code,
                jobs_retrieved=len(retrieved_jobs),
                new_jobs=comp_new_count,
                relevant_jobs=comp_relevant_count,
                verified_matches=comp_verified_count,
                potential_matches=comp_potential_count,
                pagination_completed=True,
                error_msg=error_msg
            )
            print(f"[{idx}/{len(companies)}] {comp_name}: {len(retrieved_jobs)} jobs retrieved, {comp_relevant_count} relevant ({comp_verified_count} verified, {comp_potential_count} potential)")

    # 2. Gather Unnotified Jobs for the 4 Email Sections
    unnotified_jobs = db.get_unnotified_jobs()
    verified_section = []
    potential_section = []
    below_target_section = []
    new_updated_section = []

    for j in unnotified_jobs:
        classification = j.get("classification")
        comp_status = j.get("compensation_status")
        
        if classification == "VERIFIED MATCH":
            if comp_status == "BELOW_12_LPA":
                below_target_section.append(j)
            else:
                verified_section.append(j)
        elif classification == "POTENTIAL MATCH":
            if comp_status == "BELOW_12_LPA":
                below_target_section.append(j)
            else:
                potential_section.append(j)

    scan_summary = {
        "companies_scanned": total_companies_scanned,
        "jobs_retrieved": total_jobs_retrieved,
        "verified_count": len(verified_section),
        "potential_count": len(potential_section),
        "duration_seconds": round(time.time() - start_time, 2)
    }

    # 3. Deliver Email Notification Digest
    email_sent = email_service.send_digest(
        verified_matches=verified_section,
        potential_matches=potential_section,
        below_target_jobs=below_target_section,
        new_updated_jobs=new_updated_section,
        scan_summary=scan_summary
    )

    if email_sent:
        notified_keys = [j["job_key"] for j in unnotified_jobs]
        db.mark_notified(notified_keys)
        print(f"[EMAIL] Marked {len(notified_keys)} opportunities as NOTIFIED.")

    # 4. Synchronize and Export Persistent Artifacts
    db.export_artifacts(csv_path="applications.csv", json_path="job_tracker.json")
    print(f"\n[STORAGE] Successfully synchronized database to applications.csv and job_tracker.json.")

    # 5. Output Source Health Report
    print("\n" + "=" * 75)
    print(health_monitor.format_markdown_table(limit_not_configured=True))
    print("=" * 75)
    print(f"✨ Hunter 4.0 scan completed in {scan_summary['duration_seconds']}s.")
    print("=" * 75 + "\n")

# Alias for backward compatibility
run_pipeline = run_hunter

if __name__ == "__main__":
    run_hunter()
