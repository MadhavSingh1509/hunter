# HUNTER — Simple Fresher Software & AI/ML Job Monitor

Hunter scans the 71-company watchlist in `companies.json` every 12 hours, reads full job descriptions across official ATS/career portals, applies a strict fresher filter for **B.Tech Electrical Engineering (2027)** in **India**, deduplicates previously sent jobs, and emails a minimal 4-field digest:

**Subject:** `Hunter — New Fresher Job Opportunities`

```text
Company | Position Name | Posted On | Apply Link
```

---

## Core Architecture

- **`companies.json`** — The 71-company watchlist with official ATS/API scanner configurations (Workday CXS, Oracle Cloud HCM, Greenhouse, Lever, SmartRecruiters, Eightfold AI PCSX, Amazon Jobs API, Atlassian API, AMD Jibe API, Google Careers, TalentBrew, and career portals).
- **`scrapers/portal_scanner.py`** — Paginated multi-ATS scanner that fetches individual job descriptions, extracts original posting dates (`"Not disclosed"` when unavailable), verifies official application URLs, retries transient failures, and records portal failures accurately.
- **`core/fresher_filter.py`** — Strict fresher eligibility filter:
  - Accepts only Software Engineering and AI/ML roles in India (or India-eligible Remote).
  - Requires positive fresher/entry-level/new-grad/internship confirmation in the title/JD.
  - Rejects Senior, Staff, Lead, Principal, SDE II+, 2+ years mandatory experience, 1+ years mandatory non-internship experience, CSE/IT-only restrictions, PhD/Master's-only roles, and past-batch-only restrictions.
  - Excludes ambiguous jobs whose fresher eligibility cannot be established.
- **`core/database.py`** — SQLite deduplication (`data/hunter.db`) preventing duplicate alerts for unchanged jobs and syncing to `applications.csv` and `job_tracker.json`.
- **`notifications/email_service.py`** — Minimal 4-field HTML + plain-text email sender (`Company | Position Name | Posted On | Apply Link`). Skips sending when 0 new fresher openings are found.
- **`.github/workflows/job_monitor.yml`** — Runs tests + full scan every 12 hours and persists updated records.

## Running Locally

```bash
pip install -r requirements.txt
pytest -v
python monitor.py
```
