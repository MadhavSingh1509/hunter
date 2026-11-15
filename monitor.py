"""
HUNTER 2.0 — Intelligent Job Hunting & Verification Assistant
Orchestrates job discovery, qualification, URL verification, tracking, and email alerts.
"""

import os
import sys
import json
import time
import hashlib
import re
from typing import List, Dict, Any, Tuple

from config import load_candidate_profile
from qualification_engine import QualificationEngine, JobPosting, QualificationResult
from authenticity_verifier import AuthenticityVerifier
from ats_providers import ATSProvider
from application_tracker import ApplicationTracker
from email_sender import build_email_digest, send_email_digest

STATE_FILE = "state.json"
COMPANIES_FILE = "companies.json"


def load_json(path: str, default: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Error loading {path}: {e}")
            return default
    return default


def save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def slugify(name: str) -> str:
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return name


def guessed_slugs(name: str) -> List[str]:
    base = slugify(name)
    candidates = [base, base.split("-")[0], base.replace("-", "")]
    seen = []
    for c in candidates:
        if c and c not in seen:
            seen.append(c)
    return seen


def fetch_from_ats(provider: ATSProvider, company: Dict[str, Any]) -> List[JobPosting]:
    name = company["name"]
    slugs = company.get("slugs") or []
    slugs = slugs + [s for s in guessed_slugs(name) if s not in slugs]

    for slug in slugs:
        # Try Greenhouse
        try:
            jobs = provider.fetch_greenhouse(name, slug)
            if jobs:
                print(f"[ATS] Found {len(jobs)} jobs for {name} on Greenhouse (slug: {slug})")
                return jobs
        except Exception:
            pass

        # Try Lever
        try:
            jobs = provider.fetch_lever(name, slug)
            if jobs:
                print(f"[ATS] Found {len(jobs)} jobs for {name} on Lever (slug: {slug})")
                return jobs
        except Exception:
            pass

        # Try SmartRecruiters
        try:
            jobs = provider.fetch_smartrecruiters(name, slug)
            if jobs:
                print(f"[ATS] Found {len(jobs)} jobs for {name} on SmartRecruiters (slug: {slug})")
                return jobs
        except Exception:
            pass

        # Try Ashby
        try:
            jobs = provider.fetch_ashby(name, slug)
            if jobs:
                print(f"[ATS] Found {len(jobs)} jobs for {name} on Ashby (slug: {slug})")
                return jobs
        except Exception:
            pass

    return []


def fetch_generic_career_page(company: Dict[str, Any]) -> Tuple[List[JobPosting], Optional[str]]:
    """
    Fallback for custom career pages without direct ATS JSON endpoints.
    Uses Playwright when available, or HTTP requests, to extract real job links.
    Avoids chopping arbitrary single text lines from pages.
    """
    url = company.get("careers_url", "")
    if not url:
        return [], None

    name = company["name"]
    content_hash = None
    postings: List[JobPosting] = []

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Hunter/2.0")
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Extract job links
            links = page.eval_on_selector_all(
                "a[href]",
                """elements => elements.map(e => ({
                    text: e.innerText.trim(),
                    href: e.href
                }))"""
            )
            body_text = page.inner_text("body")
            content_hash = hashlib.sha256(body_text.encode("utf-8", errors="ignore")).hexdigest()
            browser.close()

            # Filter links that represent actual individual job postings
            job_link_cues = ["/job/", "/jobs/", "/careers/", "/position/", "/requisition/", "/posting/"]
            for l in links:
                t = l.get("text", "")
                h = l.get("href", "")
                if 10 < len(t) < 120 and any(cue in h.lower() for cue in job_link_cues):
                    postings.append(JobPosting(
                        company=name,
                        title=t,
                        url=h,
                        location="India",
                        description=f"Extracted job link: {t} at {h}",
                        job_id=f"page-{hashlib.sha1(h.encode()).hexdigest()[:10]}"
                    ))

    except Exception as e:
        # Playwright not available or failed; fallback to lightweight requests
        try:
            import requests
            r = requests.get(url, timeout=12, headers={"User-Agent": "Hunter/2.0"})
            if r.status_code == 200:
                content_hash = hashlib.sha256(r.text.encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            pass

    return postings, content_hash


def run_pipeline():
    print("=" * 70)
    print("HUNTER 2.0 — Automated Candidate Job Qualification & Verification")
    print("=" * 70)

    profile = load_candidate_profile()
    candidate = profile.get("candidate", {})
    print(f"[PROFILE] Candidate: {candidate.get('name')}")
    print(f"[PROFILE] Degree & Branch: {candidate.get('degree')} in {candidate.get('branch')}")
    print(f"[PROFILE] Graduation Batch: {candidate.get('graduation_year')}")
    print(f"[PROFILE] Max Experience: {candidate.get('experience_years_max')} years")
    print(f"[PROFILE] Target Location: {candidate.get('location_country')}")
    print("=" * 70)

    engine = QualificationEngine(profile)
    verifier = AuthenticityVerifier()
    ats_provider = ATSProvider()
    tracker = ApplicationTracker()

    companies = load_json(COMPANIES_FILE, [])
    state = load_json(STATE_FILE, {})

    verified_findings: List[QualificationResult] = []
    potential_findings: List[QualificationResult] = []

    total_scanned = 0
    total_evaluated = 0

    for idx, company in enumerate(companies, 1):
        name = company["name"]
        print(f"\n[{idx}/{len(companies)}] Scanning {name}...")
        prev_state = state.get(name, {"seen_ids": [], "emailed_ids": [], "hash": None})
        seen_ids = set(prev_state.get("seen_ids", []))
        emailed_ids = set(prev_state.get("emailed_ids", []))

        # Fetch job postings
        postings = fetch_from_ats(ats_provider, company)
        mode = "api"

        if not postings:
            # Fallback to generic career page
            postings, content_hash = fetch_generic_career_page(company)
            mode = "generic"
            prev_hash = prev_state.get("hash")
            if content_hash == prev_hash and not postings:
                print(f"[{name}] Page content unchanged since last scan.")
                continue
            prev_state["hash"] = content_hash

        total_scanned += len(postings)

        company_relevant_ids = []

        for job in postings:
            total_evaluated += 1
            # Stage 2 to 8: Multi-Stage Qualification
            eval_result = engine.evaluate(job)

            if eval_result.verdict == "REJECTED":
                # Concise logging of rejection
                reasons_str = "; ".join(eval_result.rejection_reasons[:2])
                print(f"  [REJECT] {job.title[:35]} — {reasons_str}")
                continue

            # Stage 7 Verification: Verify Official Application Link
            print(f"  [VERIFYING] {job.title} (Score: {eval_result.score}/100)...")
            is_valid, verify_reason, canonical_url = verifier.verify_application_url(job.url)
            if not is_valid:
                print(f"  [CLOSED/INVALID] {job.title} — {verify_reason}")
                continue

            if canonical_url:
                job.url = canonical_url

            company_relevant_ids.append(job.job_id)

            # Stage 9: Deduplication
            if job.job_id in emailed_ids:
                print(f"  [DEDUP] Previously emailed: {job.title} ({job.job_id})")
                continue

            # Record in Application Tracker
            tracker.record_job(
                job_id=job.job_id,
                company=name,
                title=job.title,
                url=job.url,
                match_score=eval_result.score,
                status="Interested",
                notes=f"{eval_result.verdict}; Highlights: {'; '.join(eval_result.match_highlights[:3])}"
            )

            if eval_result.verdict == "VERIFIED MATCH":
                print(f"  [MATCH ★] Verified: {job.title} (Score: {eval_result.score}/100)")
                verified_findings.append(eval_result)
                emailed_ids.add(job.job_id)
            elif eval_result.verdict == "POTENTIAL MATCH":
                print(f"  [POTENTIAL ?] Review needed: {job.title} (Score: {eval_result.score}/100)")
                potential_findings.append(eval_result)

            seen_ids.add(job.job_id)

        # Update company state
        state[name] = {
            "seen_ids": list(seen_ids),
            "emailed_ids": list(emailed_ids),
            "hash": prev_state.get("hash"),
            "mode": mode,
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Polite interval
        time.sleep(0.5)

    # Save state and tracker records
    save_json(STATE_FILE, state)
    tracker.save()

    print("\n" + "=" * 70)
    print(f"[SUMMARY] Total postings scanned: {total_scanned}")
    print(f"[SUMMARY] Total evaluated: {total_evaluated}")
    print(f"[SUMMARY] Verified matches to email: {len(verified_findings)}")
    print(f"[SUMMARY] Potential matches: {len(potential_findings)}")
    print("=" * 70)

    # Stage 10: Email Alert Delivery
    subject, plain_text, html_body = build_email_digest(verified_findings, potential_findings)
    print(f"[EMAIL] Prepared digest: '{subject}'")

    send_success = send_email_digest(subject, plain_text, html_body)
    if send_success:
        print("[EMAIL] Alert successfully sent.")
    else:
        print("[EMAIL] Email alert step completed (skipped if secrets not in environment).")

    print("\nHunter 2.0 scan complete.\n")


if __name__ == "__main__":
    run_pipeline()
