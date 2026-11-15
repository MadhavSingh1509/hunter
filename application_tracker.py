"""
Hunter 2.0 Application Tracker
Stores, tracks, and manages jobs across their full lifecycle:
Interested -> Applied -> Online Assessment -> Interview Scheduled -> Selected/Rejected/No Response.
Exports to CSV and maintains persistent application records.
"""

import json
import os
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional

DEFAULT_TRACKER_FILE = os.path.join(os.path.dirname(__file__), "job_tracker.json")
DEFAULT_CSV_FILE = os.path.join(os.path.dirname(__file__), "applications.csv")

VALID_STATUSES = [
    "Interested",
    "Applied",
    "Online Assessment",
    "Interview Scheduled",
    "Rejected",
    "Selected",
    "No Response"
]


class ApplicationTracker:
    def __init__(self, tracker_file: str = DEFAULT_TRACKER_FILE, csv_file: str = DEFAULT_CSV_FILE):
        self.tracker_file = tracker_file
        self.csv_file = csv_file
        self.records: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self):
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2)
        self.export_csv()

    def export_csv(self, output_path: Optional[str] = None):
        target = output_path or self.csv_file
        fieldnames = [
            "job_id", "company", "title", "status", "interview_status",
            "url", "date_discovered", "date_applied", "match_score", "notes"
        ]
        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in self.records.values():
                writer.writerow({
                    "job_id": rec.get("job_id", ""),
                    "company": rec.get("company", ""),
                    "title": rec.get("title", ""),
                    "status": rec.get("status", "Interested"),
                    "interview_status": rec.get("interview_status", ""),
                    "url": rec.get("url", ""),
                    "date_discovered": rec.get("date_discovered", ""),
                    "date_applied": rec.get("date_applied", ""),
                    "match_score": rec.get("match_score", ""),
                    "notes": rec.get("notes", "")
                })

    def record_job(
        self,
        job_id: str,
        company: str,
        title: str,
        url: str,
        match_score: int,
        status: str = "Interested",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Records a newly discovered / verified job. If it already exists, retains its user status.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        if job_id in self.records:
            existing = self.records[job_id]
            # Update score and url if improved
            existing["match_score"] = match_score
            if url:
                existing["url"] = url
            return existing

        new_record = {
            "job_id": job_id,
            "company": company,
            "title": title,
            "url": url,
            "date_discovered": today,
            "date_applied": "",
            "status": status if status in VALID_STATUSES else "Interested",
            "interview_status": "",
            "match_score": match_score,
            "notes": notes
        }
        self.records[job_id] = new_record
        self.save()
        return new_record

    def update_status(
        self,
        job_id: str,
        status: str,
        notes: Optional[str] = None,
        interview_status: Optional[str] = None
    ) -> bool:
        """
        Updates the status of an existing job application.
        """
        if job_id not in self.records:
            # Try finding by partial ID or company match
            match = None
            for k in self.records:
                if job_id.lower() in k.lower():
                    match = k
                    break
            if not match:
                return False
            job_id = match

        rec = self.records[job_id]
        if status in VALID_STATUSES:
            rec["status"] = status
            if status == "Applied" and not rec.get("date_applied"):
                rec["date_applied"] = datetime.now().strftime("%Y-%m-%d")

        if notes:
            existing_notes = rec.get("notes", "")
            rec["notes"] = f"{existing_notes}; {notes}".strip("; ")

        if interview_status is not None:
            rec["interview_status"] = interview_status

        self.save()
        return True

    def list_applications(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        results = list(self.records.values())
        if status_filter:
            results = [r for r in results if r.get("status", "").lower() == status_filter.lower()]
        return sorted(results, key=lambda x: x.get("date_discovered", ""), reverse=True)
