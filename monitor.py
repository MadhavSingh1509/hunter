"""
SDE / Fresher Job Opening Monitor
----------------------------------
Checks career pages of companies listed in companies.json for new
fresher / SDE-relevant job postings, and emails a digest of anything new.

Strategy per company:
  1. Try known ATS JSON APIs (Greenhouse, Lever, SmartRecruiters) using
     slug hints or guessed slugs. These give exact, reliable job titles.
  2. If no API works, fall back to rendering the careers page with a
     headless browser (handles JS-heavy sites) and scanning the visible
     text for fresher/SDE-relevant lines, plus detecting page changes.

State (state.json) tracks what's already been reported so you only get
notified about genuinely new postings / changes.
"""

import json
import os
import re
import hashlib
import smtplib
import sys
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests

STATE_FILE = "state.json"
COMPANIES_FILE = "companies.json"
REQUEST_TIMEOUT = 15

FRESHER_KEYWORDS = [
    "sde", "sde-1", "sde 1", "sde i ", "software engineer", "software developer",
    "software engineer i", "new grad", "new graduate", "graduate engineer",
    "campus hire", "fresher", "entry level", "entry-level", "early career",
    "early in career", "associate software", "associate engineer",
    "university grad", "college hire", "class of 20", "early talent",
    "early-in-career", "engineer i ", "engineer i,", "engineer, new grad",
]

EXCLUDE_KEYWORDS = [
    "senior", "sr.", "sr ", "staff", "principal", "lead ", "manager",
    "director", "architect", "sde-2", "sde-3", "sde ii", "sde iii",
    "sde 2", "sde 3", "5+ years", "6+ years", "7+ years", "8+ years",
    "10+ years", "vp,", "head of", "distinguished",
]

# Derived from the candidate's resume (skills / stack / focus areas).
# A title matching these — even if it doesn't say "fresher"/"SDE" outright —
# is flagged as a resume-fit role (e.g. "React Developer", "Backend Engineer",
# "Full Stack Engineer") so genuinely relevant openings aren't missed just
# because the job title itself doesn't say "new grad".
SKILL_KEYWORDS = [
    "full stack", "full-stack", "fullstack", "mern", "react", "node.js",
    "nodejs", "node ", "javascript", "backend", "back-end", "back end",
    "frontend", "front-end", "front end", "web developer", "web development",
    "rest api", "restful", "mongodb", "express.js", "express js",
    "software developer", "sde", "application developer", "java developer",
    "python developer", "c++ developer", "dsa", "data structures",
    "competitive programming",
]


INDIA_KEYWORDS = [
    "india", "bangalore", "bengaluru", "hyderabad", "pune", "gurgaon",
    "gurugram", "noida", "delhi", "ncr", "mumbai", "chennai", "kolkata",
    "ahmedabad", "kochi", "jaipur", "indore", "chandigarh", "coimbatore",
    "vizag", "visakhapatnam", "trivandrum", "thiruvananthapuram",
]

NON_INDIA_KEYWORDS = [
    "usa", "united states", "san francisco", "seattle", "new york",
    "austin", "boston", "chicago", "los angeles", "remote - us",
    "remote (us)", "remote, us", "london", "united kingdom", "uk ",
    "singapore", "germany", "berlin", "canada", "toronto", "vancouver",
    "sydney", "melbourne", "australia", "dublin", "ireland", "amsterdam",
    "netherlands", "poland", "warsaw", "tokyo", "japan", "shanghai",
    "china", "dubai", "uae", "israel", "tel aviv", "brazil", "mexico",
    "emea only", "remote - emea",
]


def is_india_location(location_str):
    """True/False if we can tell, None if the location string doesn't say."""
    if not location_str:
        return None
    loc = location_str.lower()
    if any(k in loc for k in INDIA_KEYWORDS):
        return True
    if any(k in loc for k in NON_INDIA_KEYWORDS):
        return False
    return None


def classify(title):
    """Return a set of reason tags for why this title is relevant, or
    an empty set if it should be skipped entirely."""
    t = title.lower()
    if any(x in t for x in EXCLUDE_KEYWORDS):
        return set()
    reasons = set()
    if any(k in t for k in FRESHER_KEYWORDS):
        reasons.add("fresher/SDE")
    if any(k in t for k in SKILL_KEYWORDS):
        reasons.add("skills match")
    return reasons


def slugify(name):
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return name


def guessed_slugs(name):
    base = slugify(name)
    candidates = [base]
    # common variants
    candidates.append(base.split("-")[0])
    candidates.append(base.replace("-", ""))
    seen = []
    for c in candidates:
        if c and c not in seen:
            seen.append(c)
    return seen


def try_greenhouse(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    if r.status_code == 200:
        data = r.json()
        jobs = data.get("jobs", [])
        if jobs:
            return [
                {
                    "id": f"gh-{j['id']}",
                    "title": j["title"],
                    "url": j.get("absolute_url", ""),
                    "location": (j.get("location") or {}).get("name", ""),
                }
                for j in jobs
            ]
    return None


def try_lever(slug):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list) and data:
            return [
                {
                    "id": f"lever-{j['id']}",
                    "title": j.get("text", ""),
                    "url": j.get("hostedUrl", ""),
                    "location": (j.get("categories") or {}).get("location", ""),
                }
                for j in data
            ]
    return None


def try_smartrecruiters(slug):
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    if r.status_code == 200:
        data = r.json()
        content = data.get("content", [])
        if content:
            jobs = []
            for j in content:
                loc = j.get("location") or {}
                loc_str = ", ".join(
                    str(v) for v in (loc.get("city"), loc.get("region"), loc.get("country")) if v
                )
                jobs.append({
                    "id": f"sr-{j['id']}",
                    "title": j.get("name", ""),
                    "url": j.get("ref", ""),
                    "location": loc_str,
                })
            return jobs
    return None


def fetch_api_jobs(company):
    """Try ATS APIs. Returns list of job dicts, or None if none worked."""
    slugs = company.get("slugs") or []
    slugs = slugs + [s for s in guessed_slugs(company["name"]) if s not in slugs]
    for slug in slugs:
        for fn in (try_greenhouse, try_lever, try_smartrecruiters):
            try:
                jobs = fn(slug)
                if jobs:
                    return jobs
            except Exception:
                continue
    return None


def fetch_generic(company):
    """Render the careers page with a headless browser and scan text.
    Returns (matched_lines, page_hash) or (None, None) on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, None

    url = company["careers_url"]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent="Mozilla/5.0 (compatible; JobMonitorBot/1.0)")
            page.goto(url, timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(2000)
            text = page.inner_text("body")
            browser.close()
    except Exception:
        return None, None

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    matches = []
    for i, l in enumerate(lines):
        if len(l) >= 150:
            continue
        reasons = classify(l)
        if not reasons:
            continue
        # look at this line plus the next couple lines for a location hint
        # (career pages often show location right after/near the title)
        nearby = " ".join(lines[i:i + 3]).lower()
        if any(k in nearby for k in NON_INDIA_KEYWORDS):
            continue
        if not any(k in nearby for k in INDIA_KEYWORDS):
            reasons.add("location unverified")
        matches.append(f"{l} [{'/'.join(sorted(reasons))}]")
    matches = sorted(set(matches))
    content_hash = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    return matches, content_hash


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def send_email(digest_html, digest_text):
    host = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    to_addr = os.environ.get("EMAIL_TO", user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "New fresher / SDE / skills-match openings found"
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(digest_text, "plain"))
    msg.attach(MIMEText(digest_html, "html"))

    with smtplib.SMTP_SSL(host, port) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())


def main():
    companies = load_json(COMPANIES_FILE, [])
    state = load_json(STATE_FILE, {})

    findings = []  # list of (company_name, category, careers_url, [new items])

    for company in companies:
        name = company["name"]
        prev = state.get(name, {"seen_ids": [], "hash": None})
        new_items = []

        jobs = fetch_api_jobs(company)
        if jobs is not None:
            relevant = []
            for j in jobs:
                reasons = classify(j["title"])
                if not reasons:
                    continue
                india_check = is_india_location(j.get("location", ""))
                if india_check is False:
                    continue  # explicitly a non-India location, skip
                if india_check is None:
                    reasons.add("location unverified")
                j["reasons"] = sorted(reasons)
                relevant.append(j)
            seen_ids = set(prev.get("seen_ids", []))
            for j in relevant:
                if j["id"] not in seen_ids:
                    tag = "/".join(j["reasons"])
                    loc = f" ({j['location']})" if j.get("location") else ""
                    new_items.append(f"[{tag}] {j['title']}{loc} — {j['url']}")
            state[name] = {"seen_ids": [j["id"] for j in relevant], "hash": None, "mode": "api"}
        else:
            matches, content_hash = fetch_generic(company)
            if matches is not None:
                prev_hash = prev.get("hash")
                if content_hash != prev_hash and matches:
                    new_items = [f"(page changed) {m}" for m in matches]
                state[name] = {"seen_ids": [], "hash": content_hash, "mode": "generic"}
            else:
                # couldn't check this company at all this run; keep old state
                state[name] = prev
                state[name]["mode"] = "failed"

        if new_items:
            findings.append((name, company.get("category", ""), company["careers_url"], new_items))

        time.sleep(1)  # be polite to servers

    save_json(STATE_FILE, state)

    if not findings:
        print("No new fresher/SDE openings found this run.")
        return

    # Build email
    text_lines = ["New SDE / Fresher openings found:\n"]
    html_parts = ["<h2>New SDE / Fresher openings</h2>"]
    for name, category, url, items in findings:
        text_lines.append(f"\n{name} ({category}) — {url}")
        html_parts.append(f"<h3>{name} <small>({category})</small></h3><ul>")
        for it in items:
            text_lines.append(f"  - {it}")
            html_parts.append(f"<li>{it}</li>")
        html_parts.append("</ul>")

    digest_text = "\n".join(text_lines)
    digest_html = "".join(html_parts)

    try:
        send_email(digest_html, digest_text)
        print(f"Email sent with {sum(len(f[3]) for f in findings)} new listing(s) across {len(findings)} companies.")
    except Exception as e:
        print(f"Failed to send email: {e}", file=sys.stderr)
        print(digest_text)
        sys.exit(1)


if __name__ == "__main__":
    main()
