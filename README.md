# HUNTER 2.0 — Personal Job Hunting Assistant

Hunter 2.0 transforms simple keyword-based job alerting into an intelligent, deterministic qualification and verification system.

Its core objective: **Find real, active job opportunities that you are genuinely eligible for, and deliver direct official application links.**

---

## Key Highlights in Hunter 2.0

1. **Centralized Candidate Profile (`candidate_profile.json`)**
   - Degree: B.Tech in Electrical Engineering (EE).
   - Strict 0-year professional experience filter (personal MERN and DSA projects are distinguished from mandatory professional employment).
   - Configurable graduation batch and location preferences.

2. **10-Stage Deterministic Qualification Engine (`qualification_engine.py`)**
   - **Stage 1 (Discovery)**: Official ATS APIs (Greenhouse, Lever, SmartRecruiters, Ashby) and career portals.
   - **Stage 2 (Title Classification)**: Tier 1 primary targets (SDE, Software Engineer, Backend/Full Stack/Frontend, etc.) and Tier 2 targets (GET software track, QA Automation, Internships). Rejects non-dev, sales, HR, and core electrical roles.
   - **Stage 3 (Experience Analysis)**: Rejects mandatory 2+ years requirements. Flags 0–2 years as borderline.
   - **Stage 4 (Educational Eligibility)**: Verifies that Electrical Engineering is eligible (accepts any engineering branch / EE explicit; rejects CSE/IT-only restrictions and mandatory Master's degrees).
   - **Stage 5 (Location Analysis)**: Enforces India location (rejects foreign roles in US/UK/Singapore).
   - **Stage 6 (Description & Skills Alignment)**: Analyzes skills (C++, Java, Python, JS, React, Node, Express, Mongo, SQL, DSA, REST APIs) and rejects work-auth restrictions.
   - **Stage 7 (Graduation Year & Internship Filter)**: Validates batch year (e.g. 2026) and student eligibility.
   - **Stage 8 (Scoring & Rejection Gates)**: Transparent 100-point scoring. Mandatory rejection gates (Experience, Branch, Batch, Location, Closed status) override scoring.
   - **Stage 9 (Deduplication)**: Eliminates repeated alerts across 12-hour runs.
   - **Stage 10 (Email Delivery)**: Sends verified opportunities with match breakdown and direct apply links.

3. **Authenticity & Application Verification (`authenticity_verifier.py`)**
   - Verifies that listings are currently active and not expired, filled, or closed (404/410 checks and closure notice parsing).
   - Provides direct links to official ATS application forms.

4. **Integrated Application Tracker (`tracker.py` & `application_tracker.py`)**
   - Tracks your application pipeline: `Interested` &rarr; `Applied` &rarr; `Online Assessment` &rarr; `Interview Scheduled` &rarr; `Selected/Rejected`.
   - Maintains `job_tracker.json` and auto-exports to `applications.csv`.

---

## CLI Usage

### View Tracked Applications
```bash
python tracker.py list
```

### Mark a Job as Applied
```bash
python tracker.py apply <job_id> "Applied via referral"
```

### Update Status
```bash
python tracker.py status <job_id> "Online Assessment" "OA link received"
python tracker.py status <job_id> "Interview Scheduled" "Round 1 on Monday"
```

### Export to CSV
```bash
python tracker.py export
```

### Run Test Suite (36 Automated Tests)
```bash
pytest -v
```

### Run Monitor Manually
```bash
python monitor.py
```

---

## Configuration (`candidate_profile.json`)

You can edit your candidate profile, target categories, or scoring weights anytime in `candidate_profile.json` without modifying application code:

```json
{
  "candidate": {
    "name": "Madhav Singh",
    "degree": "B.Tech",
    "branch": "Electrical Engineering",
    "graduation_year": 2026,
    "experience_years_max": 0,
    "location_country": "India"
  }
}
```

You can also override graduation year via the environment variable `HUNTER_GRADUATION_YEAR`.

---

## GitHub Actions & Automation

The repository runs automatically every 12 hours via GitHub Actions (`.github/workflows/job_monitor.yml`).

### Required GitHub Secrets:
Set these under **Settings &rarr; Secrets and variables &rarr; Actions &rarr; Repository secrets**:

| Secret Name | Value |
|---|---|
| `EMAIL_ADDRESS` | Your Gmail address |
| `EMAIL_PASSWORD` | 16-character Google App Password |
| `EMAIL_TO` | Target recipient email address |
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` |

### Persistence Across GitHub Actions Runs:
The workflow automatically commits updated `state.json`, `job_tracker.json`, and `applications.csv` back to your GitHub repository with `[skip ci]`, ensuring history and application statuses survive ephemeral GitHub Actions runners.
