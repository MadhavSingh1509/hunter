# SDE / Fresher Job Opening Monitor

Checks the career pages of the 71 companies from your tracker every 12 hours
and emails **princeutube007@gmail.com** a digest whenever a new opening
appears that's either (a) fresher/SDE-level, or (b) a strong match for your
resume's skill set — even if the title doesn't say "fresher".

## How it works

- For companies on **Greenhouse, Lever, or SmartRecruiters** (many startups
  and mid-size tech cos use these), it queries their public job APIs
  directly — fast, and gives you exact job titles and links.
- For everyone else (Workday, custom React career sites, etc.), it renders
  the page with a headless browser and scans the visible text for relevant
  keywords, and flags it whenever the page content changes.
  This is best-effort: it can't always tell "new job" from "any page edit",
  so those alerts are worth a quick manual glance.
- It remembers what it already told you (`state.json`) so you don't get
  repeat notifications for the same posting.

## Two ways a listing gets flagged

Each alert is tagged so you know why it showed up:

- **`[fresher/SDE]`** — title contains fresher/entry-level/new-grad/SDE-1
  style language (e.g. "SDE-1", "New Grad Software Engineer").
- **`[skills match]`** — title matches your resume's stack even without
  "fresher" in the name (e.g. "React Developer", "Backend Engineer",
  "Full Stack Developer", "MERN Stack Engineer", "Node.js Developer").
  This is based on your resume: MERN stack (React/Node/Express/MongoDB),
  JavaScript, REST APIs, C++/Java/Python, DSA/competitive programming.
  A listing can carry both tags at once.
- **`[location unverified]`** — added when the listing's location couldn't
  be confidently identified as India or not-India. It's still included
  (rather than silently dropped) since many postings don't tag location
  cleanly — just double-check that one before applying.

## India-only filtering

Roles clearly located outside India (e.g. "USA", "London", "Singapore",
"Remote - US") are automatically filtered out and never emailed to you.
Roles that mention an Indian city (Bangalore, Hyderabad, Pune, Gurgaon,
Noida, etc.) or "India" are included normally. To adjust the city/country
lists, edit `INDIA_KEYWORDS` and `NON_INDIA_KEYWORDS` in `monitor.py`.

To tune this further (add/remove skills), edit `SKILL_KEYWORDS` in
`monitor.py`.

## One-time setup (about 10 minutes)

### 1. Create a GitHub repo
Create a new **private** repo (e.g. `sde-fresher-monitor`) and push these
files to it (`companies.json`, `monitor.py`, `requirements.txt`,
`state.json`, `.github/workflows/job_monitor.yml`).

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/sde-fresher-monitor.git
git push -u origin main
```

### 2. Create a Gmail App Password (if using Gmail)
Regular Gmail passwords won't work with SMTP. Create an app password:
1. Go to https://myaccount.google.com/apppasswords
2. Generate a 16-character app password for "Mail"
3. Save it — you'll need it in step 3.

(Using Outlook/another provider? Just use its SMTP host/port instead —
see step 3.)

### 3. Add GitHub Secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add these:

| Secret name      | Value                                      |
|-------------------|---------------------------------------------|
| `EMAIL_ADDRESS`   | The Gmail address the alert is sent *from*  |
| `EMAIL_PASSWORD`  | The 16-character app password from step 2   |
| `EMAIL_TO`        | `princeutube007@gmail.com`                  |
| `SMTP_SERVER`     | `smtp.gmail.com` (or your provider's SMTP host) |
| `SMTP_PORT`       | `465`                                        |

### 4. Test it
Go to the **Actions** tab in your repo → "SDE Fresher Job Monitor" →
**Run workflow** (manual trigger). Check the run logs, and check your inbox.

That's it — it will now run automatically every 12 hours.

## Customizing

- **Add/remove companies**: edit `companies.json`.
- **Change keywords**: edit `FRESHER_KEYWORDS` / `EXCLUDE_KEYWORDS` in
  `monitor.py` to tune what counts as "fresher/SDE relevant".
- **Change frequency**: edit the `cron` line in
  `.github/workflows/job_monitor.yml` (currently every 12 hours).
- **Improve accuracy for a specific company**: if you know a company uses
  Greenhouse/Lever/SmartRecruiters and its exact slug (visible in its
  careers URL, e.g. `boards.greenhouse.io/<slug>`), add it to the `slugs`
  list for that company in `companies.json` — this skips the guesswork and
  the less-reliable generic fallback entirely.

## Known limitations

- Some companies (Workday-based ones especially — Cisco, Dell, Intel, etc.)
  are hard to scrape reliably even with a headless browser, since job
  boards load dynamically behind search/filter UI. For these, treat alerts
  as "something changed, go check" rather than an exact job list.
- If a company's careers page blocks automated browsers, that company will
  simply show no results — it won't break the rest of the run.
- Free GitHub Actions has generous limits for a private repo at this scale
  (2 runs/day, ~71 quick checks each), so this should stay well within the
  free tier.
