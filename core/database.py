"""
Hunter 4.0 - Database & Persistent Storage Engine (SQLite)
Manages companies, campus recruiters, jobs, transitions, source health, and syncs to CSV/JSON.
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "hunter.db")

class HunterDatabase:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Creates the required tables if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Companies Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                section TEXT,
                category TEXT,
                careers_url TEXT,
                ats_type TEXT,
                ats_identifier TEXT,
                priority TEXT,
                status TEXT,
                is_mandatory_priority INTEGER DEFAULT 0
            )
            """)

            # Campus Recruiters Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS campus_recruiters (
                company_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                priority_tier TEXT,
                recurrence TEXT,
                evidence_json TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
            """)

            # Jobs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_key TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                company_name TEXT NOT NULL,
                ats_job_id TEXT,
                title TEXT NOT NULL,
                normalized_title TEXT,
                canonical_url TEXT NOT NULL,
                location TEXT,
                is_india_eligible INTEGER DEFAULT 1,
                employment_type TEXT,
                compensation_text TEXT,
                compensation_status TEXT,
                base_salary TEXT,
                variable_comp TEXT,
                joining_bonus TEXT,
                stock_equity TEXT,
                total_ctc TEXT,
                role_relevance TEXT,
                degree_eligibility TEXT,
                graduation_eligibility TEXT,
                experience_eligibility TEXT,
                application_status TEXT DEFAULT 'OPEN',
                classification TEXT,
                match_score REAL DEFAULT 0,
                score_reasons_json TEXT,
                eligibility_notes TEXT,
                notification_status TEXT DEFAULT 'PENDING',
                posted_on TEXT DEFAULT 'Not disclosed',
                first_discovered_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
            """)

            # Safe schema migration for existing hunter.db files
            cursor.execute("PRAGMA table_info(jobs)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if "posted_on" not in existing_cols:
                cursor.execute("ALTER TABLE jobs ADD COLUMN posted_on TEXT DEFAULT 'Not disclosed'")

            # Job History / State Transitions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_key TEXT NOT NULL,
                transition_type TEXT NOT NULL,
                previous_classification TEXT,
                new_classification TEXT,
                previous_status TEXT,
                new_status TEXT,
                notes TEXT,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (job_key) REFERENCES jobs(job_key)
            )
            """)

            # Scans Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_timestamp TEXT NOT NULL,
                total_companies_scanned INTEGER DEFAULT 0,
                total_jobs_retrieved INTEGER DEFAULT 0,
                new_jobs_found INTEGER DEFAULT 0,
                verified_matches INTEGER DEFAULT 0,
                potential_matches INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0.0,
                status TEXT DEFAULT 'SUCCESS',
                summary_json TEXT
            )
            """)

            # Source Health Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_health (
                company_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                source_url TEXT,
                scanner_type TEXT,
                health_status TEXT NOT NULL,
                http_status INTEGER,
                jobs_retrieved INTEGER DEFAULT 0,
                new_jobs_discovered INTEGER DEFAULT 0,
                relevant_jobs_found INTEGER DEFAULT 0,
                verified_matches INTEGER DEFAULT 0,
                potential_matches INTEGER DEFAULT 0,
                pagination_completed INTEGER DEFAULT 1,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                last_attempted_at TEXT,
                last_successful_at TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
            """)

            conn.commit()

    @staticmethod
    def generate_job_key(company_id: str, ats_job_id: Optional[str], canonical_url: str) -> str:
        """Generates a stable, canonical unique hash key for a job."""
        comp = company_id.strip().lower()
        clean_url = canonical_url.strip().split("?")[0].rstrip("/")
        if ats_job_id and ats_job_id.strip():
            raw = f"{comp}::{ats_job_id.strip()}::{clean_url}"
        else:
            raw = f"{comp}::{clean_url}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def seed_registries(self, company_registry_path: str, campus_registry_path: str):
        """Loads and persists companies and campus recruiter data into SQLite."""
        if not os.path.exists(company_registry_path):
            raise FileNotFoundError(f"Missing {company_registry_path}")

        with open(company_registry_path, "r", encoding="utf-8") as f:
            companies = json.load(f)

        campus_data = []
        if os.path.exists(campus_registry_path):
            with open(campus_registry_path, "r", encoding="utf-8") as f:
                campus_data = json.load(f)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for c in companies:
                cursor.execute("""
                INSERT INTO companies (id, name, section, category, careers_url, ats_type, ats_identifier, priority, status, is_mandatory_priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    section=excluded.section,
                    category=excluded.category,
                    careers_url=excluded.careers_url,
                    ats_type=excluded.ats_type,
                    ats_identifier=excluded.ats_identifier,
                    priority=excluded.priority,
                    status=excluded.status,
                    is_mandatory_priority=excluded.is_mandatory_priority
                """, (
                    c["id"], c["name"], c.get("section"), c.get("category"), c.get("careers_url"),
                    c.get("ats_type"), c.get("ats_identifier"), c.get("priority", "normal"),
                    c.get("status", "NOT_CONFIGURED"), 1 if c.get("is_mandatory_priority") else 0
                ))

            for cr in campus_data:
                cursor.execute("""
                INSERT INTO campus_recruiters (company_id, company_name, priority_tier, recurrence, evidence_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(company_id) DO UPDATE SET
                    company_name=excluded.company_name,
                    priority_tier=excluded.priority_tier,
                    recurrence=excluded.recurrence,
                    evidence_json=excluded.evidence_json
                """, (
                    cr["company_id"], cr["company_name"], cr.get("priority_tier"),
                    cr.get("recurrence", "UNVERIFIED"), json.dumps(cr.get("evidence", []))
                ))

            conn.commit()

    def record_job(self, job_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Upserts job record, detects lifecycle transitions, and logs history.
        Returns (job_key, transition_type: 'NEW' | 'OPEN' | 'VERIFIED_UPGRADE' | 'UPDATED' | 'REOPENED').
        """
        company_id = job_data.get("company_id", "unknown").lower()
        company_name = job_data.get("company_name", company_id)
        ats_job_id = str(job_data.get("ats_job_id") or "").strip()
        canonical_url = job_data.get("canonical_url", "").strip()

        job_key = self.generate_job_key(company_id, ats_job_id, canonical_url)
        now_iso = datetime.now().isoformat()

        new_classification = job_data.get("classification", "VERIFIED MATCH")
        new_status = job_data.get("application_status", "OPEN")
        posted_on = str(job_data.get("posted_on") or "Not disclosed").strip() or "Not disclosed"
        match_score = float(job_data.get("match_score", 0.0))
        score_reasons = json.dumps(job_data.get("score_reasons", {}))

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_key = ?", (job_key,))
            existing = cursor.fetchone()

            if not existing:
                transition = "NEW"
                cursor.execute("""
                INSERT INTO jobs (
                    job_key, company_id, company_name, ats_job_id, title, normalized_title,
                    canonical_url, location, is_india_eligible, employment_type,
                    compensation_text, compensation_status, base_salary, variable_comp,
                    joining_bonus, stock_equity, total_ctc, role_relevance, degree_eligibility,
                    graduation_eligibility, experience_eligibility, application_status,
                    classification, match_score, score_reasons_json, eligibility_notes,
                    notification_status, posted_on, first_discovered_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_key, company_id, company_name, ats_job_id,
                    job_data.get("title", ""), job_data.get("normalized_title", job_data.get("title", "")),
                    canonical_url, job_data.get("location", "India"),
                    1 if job_data.get("is_india_eligible", True) else 0,
                    job_data.get("employment_type", "Full-time"),
                    job_data.get("compensation_text", "Not disclosed"),
                    job_data.get("compensation_status", "UNDISCLOSED"),
                    job_data.get("base_salary", ""), job_data.get("variable_comp", ""),
                    job_data.get("joining_bonus", ""), job_data.get("stock_equity", ""),
                    job_data.get("total_ctc", ""), job_data.get("role_relevance", "MATCH"),
                    job_data.get("degree_eligibility", "ELIGIBLE"),
                    job_data.get("graduation_eligibility", "ELIGIBLE"),
                    job_data.get("experience_eligibility", "ELIGIBLE"),
                    new_status, new_classification, match_score, score_reasons,
                    job_data.get("eligibility_notes", ""), "PENDING", posted_on, now_iso, now_iso
                ))
            else:
                prev_class = existing["classification"]
                prev_status = existing["application_status"]
                
                if prev_status == "CLOSED" and new_status == "OPEN":
                    transition = "REOPENED"
                    notif_status = "PENDING"
                elif prev_class == "POTENTIAL MATCH" and new_classification == "VERIFIED MATCH":
                    transition = "VERIFIED_UPGRADE"
                    notif_status = "PENDING"
                elif prev_class != new_classification or existing["match_score"] != match_score:
                    transition = "UPDATED"
                    notif_status = existing["notification_status"]
                else:
                    transition = "OPEN"
                    notif_status = existing["notification_status"]

                final_posted = posted_on if posted_on != "Not disclosed" else (existing["posted_on"] or "Not disclosed")

                cursor.execute("""
                UPDATE jobs SET
                    company_name = ?,
                    title = ?,
                    normalized_title = ?,
                    location = ?,
                    is_india_eligible = ?,
                    employment_type = ?,
                    compensation_text = ?,
                    compensation_status = ?,
                    role_relevance = ?,
                    degree_eligibility = ?,
                    graduation_eligibility = ?,
                    experience_eligibility = ?,
                    application_status = ?,
                    classification = ?,
                    match_score = ?,
                    score_reasons_json = ?,
                    eligibility_notes = ?,
                    notification_status = ?,
                    posted_on = ?,
                    last_seen_at = ?
                WHERE job_key = ?
                """, (
                    company_name, job_data.get("title", existing["title"]),
                    job_data.get("normalized_title", existing["normalized_title"]),
                    job_data.get("location", existing["location"]),
                    1 if job_data.get("is_india_eligible", True) else 0,
                    job_data.get("employment_type", existing["employment_type"]),
                    job_data.get("compensation_text", existing["compensation_text"]),
                    job_data.get("compensation_status", existing["compensation_status"]),
                    job_data.get("role_relevance", existing["role_relevance"]),
                    job_data.get("degree_eligibility", existing["degree_eligibility"]),
                    job_data.get("graduation_eligibility", existing["graduation_eligibility"]),
                    job_data.get("experience_eligibility", existing["experience_eligibility"]),
                    new_status, new_classification, match_score, score_reasons,
                    job_data.get("eligibility_notes", existing["eligibility_notes"]),
                    notif_status, final_posted, now_iso, job_key
                ))

            # Record history transition
            cursor.execute("""
            INSERT INTO job_history (job_key, transition_type, previous_classification, new_classification, previous_status, new_status, notes, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_key, transition,
                existing["classification"] if existing else None, new_classification,
                existing["application_status"] if existing else None, new_status,
                f"Score: {match_score:.1f}", now_iso
            ))

            conn.commit()

        return job_key, transition

    def mark_notified(self, job_keys: List[str]):
        """Marks notified jobs as NOTIFIED."""
        if not job_keys:
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("UPDATE jobs SET notification_status = 'NOTIFIED' WHERE job_key = ?", [(k,) for k in job_keys])
            conn.commit()

    def update_source_health(self, company_id: str, company_name: str, source_url: str,
                             scanner_type: str, health_status: str, http_status: Optional[int],
                             jobs_retrieved: int, new_jobs: int, relevant_jobs: int,
                             verified_matches: int, potential_matches: int,
                             pagination_completed: bool = True, error_msg: Optional[str] = None):
        """Updates diagnostic health status for a company scanner."""
        now_iso = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            last_success = now_iso if health_status in ["HEALTHY", "DEGRADED"] else None
            
            cursor.execute("""
            INSERT INTO source_health (
                company_id, company_name, source_url, scanner_type, health_status,
                http_status, jobs_retrieved, new_jobs_discovered, relevant_jobs_found,
                verified_matches, potential_matches, pagination_completed, retry_count,
                error_message, last_attempted_at, last_successful_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id) DO UPDATE SET
                company_name=excluded.company_name,
                source_url=excluded.source_url,
                scanner_type=excluded.scanner_type,
                health_status=excluded.health_status,
                http_status=excluded.http_status,
                jobs_retrieved=excluded.jobs_retrieved,
                new_jobs_discovered=excluded.new_jobs_discovered,
                relevant_jobs_found=excluded.relevant_jobs_found,
                verified_matches=excluded.verified_matches,
                potential_matches=excluded.potential_matches,
                pagination_completed=excluded.pagination_completed,
                error_message=excluded.error_message,
                last_attempted_at=excluded.last_attempted_at,
                last_successful_at=COALESCE(excluded.last_successful_at, source_health.last_successful_at)
            """, (
                company_id, company_name, source_url, scanner_type, health_status,
                http_status, jobs_retrieved, new_jobs, relevant_jobs,
                verified_matches, potential_matches, 1 if pagination_completed else 0,
                0, error_msg, now_iso, last_success
            ))
            conn.commit()

    def get_source_health_summary(self) -> List[Dict[str, Any]]:
        """Returns source health diagnostic records for all companies."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.id, c.name, c.section, c.category, c.ats_type, c.priority, c.is_mandatory_priority,
                   COALESCE(sh.health_status, CASE WHEN c.status = 'CONFIGURED' THEN 'UNKNOWN' ELSE 'NOT_CONFIGURED' END) as health_status,
                   COALESCE(sh.jobs_retrieved, 0) as jobs_retrieved,
                   COALESCE(sh.relevant_jobs_found, 0) as relevant_jobs_found,
                   COALESCE(sh.verified_matches, 0) as verified_matches,
                   COALESCE(sh.potential_matches, 0) as potential_matches,
                   sh.error_message, sh.last_attempted_at, sh.last_successful_at
            FROM companies c
            LEFT JOIN source_health sh ON c.id = sh.company_id
            ORDER BY c.is_mandatory_priority DESC, c.priority ASC, c.name ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_unnotified_jobs(self) -> List[Dict[str, Any]]:
        """Fetches all jobs that require email notification (PENDING)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM jobs
            WHERE notification_status = 'PENDING' AND classification IN ('VERIFIED MATCH', 'POTENTIAL MATCH')
            ORDER BY match_score DESC, first_discovered_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_unnotified_verified_jobs(self) -> List[Dict[str, Any]]:
        """Fetches ONLY confirmed fresher-eligible (VERIFIED MATCH) jobs that have not yet been emailed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM jobs
            WHERE notification_status = 'PENDING' AND classification = 'VERIFIED MATCH'
            ORDER BY company_name ASC, first_discovered_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Fetches all active jobs in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY company_name ASC, first_discovered_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def export_artifacts(self, csv_path: str = "applications.csv", json_path: str = "job_tracker.json"):
        """Exports SQLite database records to applications.csv and job_tracker.json for visibility and git persistence."""
        jobs = self.get_all_jobs()

        # Export JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2)

        # Export simple clean CSV
        import csv
        fieldnames = ["Company", "Position Name", "Posted On", "Apply Link", "Location", "Status", "Discovered Date"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for j in jobs:
                writer.writerow({
                    "Company": j.get("company_name"),
                    "Position Name": j.get("title"),
                    "Posted On": j.get("posted_on") or "Not disclosed",
                    "Apply Link": j.get("canonical_url"),
                    "Location": j.get("location"),
                    "Status": j.get("notification_status"),
                    "Discovered Date": j.get("first_discovered_at", "")[:10],
                })
