"""
HUNTER — Simple Fresher Software Engineering & AI/ML Job Monitor
Scans all companies in companies.json thoroughly with pagination and full JD inspection,
applies the strict fresher filter (B.Tech Electrical Engineering, 2027, India-only),
deduplicates against SQLite (data/hunter.db), and sends a minimal 4-field email:
Company | Position Name | Posted On | Apply Link
"""

import os
import re
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from core.database import HunterDatabase
from core.fresher_filter import StrictFresherFilter
from scrapers.portal_scanner import PortalScanner, CompanyScanReport
from notifications.email_service import HunterEmailService

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("hunter")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPANIES_FILE = os.path.join(BASE_DIR, "companies.json")
PROFILE_FILE = os.path.join(BASE_DIR, "candidate_profile.json")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def load_graduation_year() -> int:
    env_yr = os.environ.get("HUNTER_GRADUATION_YEAR", "").strip()
    if env_yr.isdigit():
        return int(env_yr)
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                prof = json.load(f)
            return int(prof.get("candidate", {}).get("graduation_year", 2027))
        except Exception:
            pass
    return 2027


def scan_single_company(comp: Dict[str, Any], grad_year: int) -> CompanyScanReport:
    """Thread-safe scanner worker (each worker uses its own requests Session)."""
    flt = StrictFresherFilter(graduation_year=grad_year)
    scanner = PortalScanner(flt, timeout=12)
    report = scanner.scan_company(comp)

    # Verify each candidate's official apply URL before returning
    verified_matches = []
    for job in report.fresher_matches:
        if scanner.verify_application_url(job.get("canonical_url", "")):
            verified_matches.append(job)
    report.fresher_matches = verified_matches
    return report


def run_hunter() -> Dict[str, Any]:
    start_time = time.time()
    grad_year = load_graduation_year()

    print("=" * 72)
    print(f"HUNTER — Fresher Software & AI/ML Job Scan (B.Tech EE | Batch {grad_year} | India)")
    print("=" * 72)

    with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
        companies = json.load(f)

    db = HunterDatabase()
    email_service = HunterEmailService()

    print(f"[WATCHLIST] Loaded {len(companies)} companies from companies.json")
    print("[SCAN] Scanning all company portals with pagination and full JD inspection...\n")

    reports: List[CompanyScanReport] = []

    # Polite concurrency: 5 workers avoids Workday/ATS 429 rate-limit blocks while finishing thoroughly
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(scan_single_company, comp, grad_year): comp for comp in companies}
        completed = 0
        for future in as_completed(future_map):
            comp = future_map[future]
            completed += 1
            try:
                rep = future.result()
            except Exception as e:
                rep = CompanyScanReport(
                    company=comp["name"],
                    scanner_type=comp.get("scanner", {}).get("type", "unknown"),
                    status="FAILED",
                    error=str(e),
                )
            reports.append(rep)

            if rep.status == "SCANNED_OK":
                print(
                    f"  [{completed:2d}/{len(companies)}] OK     | {rep.company:24s} ({rep.scanner_type:14s}) | "
                    f"retrieved={rep.total_retrieved:<4d} jds_read={rep.candidate_jds_checked:<3d} fresher_matches={len(rep.fresher_matches)}",
                    flush=True
                )
            else:
                print(
                    f"  [{completed:2d}/{len(companies)}] FAILED | {rep.company:24s} ({rep.scanner_type:14s}) | {rep.error}",
                    flush=True
                )

    # Sort reports alphabetically for clean recording & summary
    reports.sort(key=lambda r: r.company.lower())

    total_retrieved = sum(r.total_retrieved for r in reports)
    total_jds_checked = sum(r.candidate_jds_checked for r in reports)
    ok_companies = [r for r in reports if r.status == "SCANNED_OK"]
    failed_companies = [r for r in reports if r.status != "SCANNED_OK"]

    new_recorded = 0
    seen_urls_this_run = set()

    for rep in reports:
        comp_id = slugify(rep.company)
        db.update_source_health(
            company_id=comp_id,
            company_name=rep.company,
            source_url="",
            scanner_type=rep.scanner_type,
            health_status="HEALTHY" if rep.status == "SCANNED_OK" else "FAILED",
            http_status=200 if rep.status == "SCANNED_OK" else 0,
            jobs_retrieved=rep.total_retrieved,
            new_jobs=0,
            relevant_jobs=len(rep.fresher_matches),
            verified_matches=len(rep.fresher_matches),
            potential_matches=0,
            pagination_completed=(rep.status == "SCANNED_OK"),
            error_msg=rep.error or None,
        )

        for job in rep.fresher_matches:
            url_norm = job["canonical_url"].strip().split("?")[0].rstrip("/")
            dedup_key = f"{comp_id}::{job.get('ats_job_id', '')}::{url_norm}"
            if dedup_key in seen_urls_this_run:
                continue
            seen_urls_this_run.add(dedup_key)

            _, transition = db.record_job({
                "company_id": comp_id,
                "company_name": rep.company,
                "ats_job_id": job.get("ats_job_id", ""),
                "title": job["title"],
                "canonical_url": job["canonical_url"],
                "location": job.get("location", "India"),
                "posted_on": job.get("posted_on", "Not disclosed"),
                "classification": "VERIFIED MATCH",
                "application_status": "OPEN",
                "eligibility_notes": job.get("reason", "Confirmed fresher-eligible"),
            })
            if transition in ("NEW", "REOPENED"):
                new_recorded += 1

    # Fetch ONLY unnotified confirmed fresher jobs
    jobs_to_email = db.get_unnotified_verified_jobs()

    print("\n" + "=" * 72)
    print(f"SCAN SUMMARY ({round(time.time() - start_time, 1)}s)")
    print(f"  Companies attempted : {len(reports)}/{len(companies)}")
    print(f"  Portals scanned OK  : {len(ok_companies)}")
    print(f"  Portals failed      : {len(failed_companies)}")
    print(f"  Total listings seen : {total_retrieved}")
    print(f"  JDs inspected       : {total_jds_checked}")
    print(f"  New fresher matches : {new_recorded}")
    print(f"  Queued for email    : {len(jobs_to_email)}")
    print("=" * 72)

    if jobs_to_email:
        print("\nConfirmed Fresher Opportunities (Company | Position Name | Posted On | Apply Link):")
        for j in jobs_to_email:
            print(f"  {j['company_name']} | {j['title']} | {j.get('posted_on') or 'Not disclosed'} | {j['canonical_url']}")

    # Send simple 4-field email ONLY if there are new confirmed fresher jobs
    email_sent = email_service.send_simple_digest(jobs_to_email)
    if email_sent:
        db.mark_notified([j["job_key"] for j in jobs_to_email])
        print(f"[EMAIL] Marked {len(jobs_to_email)} jobs as NOTIFIED.")

    # Export clean CSV & JSON
    db.export_artifacts(csv_path="applications.csv", json_path="job_tracker.json")

    return {
        "attempted": len(reports),
        "ok": [r.company for r in ok_companies],
        "failed": [(r.company, r.error) for r in failed_companies],
        "total_retrieved": total_retrieved,
        "jds_checked": total_jds_checked,
        "fresher_matches": sum(len(r.fresher_matches) for r in reports),
        "queued_for_email": len(jobs_to_email),
        "email_sent": email_sent,
    }


# Backward-compatible alias
run_pipeline = run_hunter

if __name__ == "__main__":
    run_hunter()
