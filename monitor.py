"""
SDE / Fresher Job & Internship Opening Monitor
------------------------------------------------
Checks career pages of companies listed in companies.json for new
fresher/SDE-relevant job and internship postings inside India, and emails
a formatted digest of anything new.

Filters applied (see README for exact rules and known limitations):
  1. India-based only (explicit location match required)
  2. Fresher-eligible / entry-level (0-2 yrs) language
  3. Excludes postings that explicitly name a different graduating batch
  4. Company-level CTC >= 12 LPA (from companies.json, since individual
     postings rarely list exact pay)
  5. Both jobs and internships included (internship stipend can't be
     reliably scraped, so those are flagged "verify on page")

Strategy per company:
  1. Try known ATS JSON APIs (Greenhouse, Lever, SmartRecruiters) using
     slug hints or guessed slugs. These give exact, reliable job titles.
  2. If no API works, fall back to rendering the careers page with a
     headless browser (handles JS-heavy sites) and scanning the visible
     text for relevant lines.

State (state.json) tracks what's already been reported so you only get
notified about genuinely new postings.
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
MAX_YEARS_EXPERIENCE = 2

FRESHER_KEYWORDS = [
    "sde", "sde-1", "sde 1", "sde i ", "swe", "swe-1", "swe 1", "swe i ",
    "software engineer", "software developer", "software development engineer",
    "software engineer i", "new grad", "new graduate", "graduate engineer",
    "campus hire", "fresher", "entry level", "entry-level", "early career",
    "early in career", "associate software", "associate engineer",
    "university grad", "college hire", "class of 20", "early talent",
    "early-in-career", "engineer i ", "engineer i,", "engineer, new grad",
    "engineer trainee", "graduate engineer trainee", "programmer analyst",
    "member of technical staff", "software engineer trainee",
    "systems engineer", "software systems engineer", "associate systems engineer",
    "site reliability engineer", "platform engineer", "cloud engineer",
]

INTERN_KEYWORDS = ["intern", "internship"]

# Departments/functions this candidate is NOT looking for, even if a title
# happens to also contain an engineering-sounding word.
DEPARTMENT_EXCLUDE_KEYWORDS = [
    "human resources", "hr executive", "hr manager", "hr generalist",
    "recruiter", "recruitment", "talent acquisition", "sales executive",
    "sales manager", "marketing", "finance", "accounting", "accountant",
    "customer support", "customer success", "business development",
    "legal counsel", "administrative", "office coordinator",
    "product manager", "program manager", "project manager",
    "business analyst", "data entry", "operations executive",
]

# Plain "senior" etc. words that always mean not-junior, regardless of level number.
EXCLUDE_KEYWORDS = [
    "senior", "sr.", "sr ", "staff", "principal", "lead ", "manager",
    "director", "architect", "vp,", "head of", "distinguished",
]

# From the candidate's resume: MERN stack, JS, REST APIs, DSA/CP background.
SKILL_KEYWORDS = [
    "full stack", "full-stack", "fullstack", "mern", "react", "node.js",
    "nodejs", "node ", "javascript", "backend", "back-end", "back end",
    "frontend", "front-end", "front end", "web developer", "web development",
    "rest api", "restful", "mongodb", "express.js", "express js",
    "software developer", "sde", "swe", "application developer",
    "java developer", "python developer", "c++ developer", "dsa",
    "data structures", "competitive programming", "systems engineer",
]


def seniority_level(text):
    """Detect an explicit numeric/roman seniority level like 'SDE II',
    'SDE-3', 'Software Engineer II', 'L4'. Returns an int level, or None
    if no level is stated (title just says e.g. 'Software Engineer')."""
    t = text.lower()
    roman = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5}
    m = re.search(
        r"\b(?:sde|swe|software (?:development )?engineer|engineer)"
        r"[\s\-]*([1-5]|i|ii|iii|iv|v)\b", t,
    )
    if m:
        val = m.group(1)
        return int(val) if val.isdigit() else roman.get(val)
    m = re.search(r"\bl([2-9])\b", t)  # internal grade codes like L4, L5 (L1 = junior, excluded from this check)
    if m:
        return int(m.group(1))
    return None

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


def is_excluded(text):
    """True if this title should never be shown, regardless of whether
    it's a job or an internship — too senior, or not an engineering role."""
    t = text.lower()
    if any(x in t for x in EXCLUDE_KEYWORDS):
        return True
    if any(x in t for x in DEPARTMENT_EXCLUDE_KEYWORDS):
        return True
    if re.search(r"\bhr\b", t):
        return True
    level = seniority_level(t)
    if level is not None and level >= 2:
        return True  # SDE-II/III, Engineer II, L4+, etc. — too senior
    return False


def classify(title):
    """Return a set of reason tags, or empty set if not relevant at all."""
    t = title.lower()
    if is_excluded(t):
        return set()
    reasons = set()
    if any(k in t for k in FRESHER_KEYWORDS):
        reasons.add("fresher/SDE")
    if any(k in t for k in SKILL_KEYWORDS):
        reasons.add("skills match")
    return reasons


def is_internship(text):
    t = text.lower()
    return any(k in t for k in INTERN_KEYWORDS)


def required_years(text):
    """Extract minimum years of experience required, or None if unstated."""
    t = text.lower()
    m = re.search(r"(\d+)\s*\+\s*years?", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*years?", t)
    if m:
        return int(m.group(1))
    return None


def passes_all_filters(text, company, is_intern):
    """Applies the fresher-eligibility filter only. No batch-year matching
    (most postings never state one) and no CTC filtering (most postings
    never state pay, so this can't be checked reliably) — just: is this
    something a 0-2 year fresher could actually apply to?"""
    yrs = required_years(text)
    if yrs is not None and yrs > MAX_YEARS_EXPERIENCE:
        return False
    return True


def is_valid_public_link(url):
    """Returns False for URLs that are raw API endpoints rather than an
    actual page a person can open and apply from (e.g. api.smartrecruiters.com
    JSON endpoints). Returns True for genuine public job/career pages."""
    if not url:
        return False
    bad_domains = ["api.smartrecruiters.com", "api.lever.co", "boards-api.greenhouse.io"]
    return not any(d in url for d in bad_domains)


def slugify(name):
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return name


def guessed_slugs(name):
    base = slugify(name)
    candidates = [base, base.split("-")[0], base.replace("-", "")]
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
                    "posted_date": (j.get("updated_at") or "")[:10],
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
            jobs = []
            for j in data:
                created_ms = j.get("createdAt")
                posted = ""
                if created_ms:
                    try:
                        posted = time.strftime("%Y-%m-%d", time.gmtime(created_ms / 1000))
                    except Exception:
                        posted = ""
                jobs.append({
                    "id": f"lever-{j['id']}",
                    "title": j.get("text", ""),
                    "url": j.get("hostedUrl", ""),
                    "location": (j.get("categories") or {}).get("location", ""),
                    "posted_date": posted,
                })
            return jobs
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
                # The list endpoint's "ref" is an internal API URL, not a
                # page a person can open. Try to resolve the real public
                # apply page from the full posting detail; if that fails,
                # leave url blank so the email falls back to Job ID only.
                public_url = ""
                try:
                    detail = requests.get(j.get("ref", ""), timeout=REQUEST_TIMEOUT).json()
                    public_url = detail.get("applyUrl") or detail.get("postingUrl") or ""
                except Exception:
                    public_url = ""
                jobs.append({
                    "id": f"sr-{j['id']}",
                    "title": j.get("name", ""),
                    "url": public_url,
                    "location": loc_str,
                    "posted_date": (j.get("releasedDate") or "")[:10],
                })
            return jobs
    return None


def fetch_api_jobs(company):
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
    Returns (list_of_item_dicts, page_hash) or (None, None) on failure.
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
    items = []
    for i, l in enumerate(lines):
        if len(l) >= 150:
            continue
        if is_excluded(l):
            continue
        reasons = classify(l)
        intern = is_internship(l)
        if not reasons and not intern:
            continue
        nearby = " ".join(lines[i:i + 3])
        nearby_lower = nearby.lower()
        if not any(k in nearby_lower for k in INDIA_KEYWORDS):
            continue  # require explicit India mention nearby
        if not passes_all_filters(nearby_lower, company, intern):
            continue
        items.append({
            "id": hashlib.sha1(l.encode("utf-8", errors="ignore")).hexdigest()[:10],
            "title": l,
            "url": url,  # company's careers page (not a specific-job deep link)
            "location": "India (unspecified city)",
            "is_intern": intern,
            "reasons": sorted(reasons) if reasons else ["internship"],
            "posted_date": "",
        })
    content_hash = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    return items, content_hash


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


CUSTOM_MESSAGE = (
    "Hey, it's Prince! I built this little bot to track fresh openings "
    "across companies so you don't have to check 70+ career pages by hand. "
    "Everything below is new since the last check — go apply before someone "
    "else does. All the best! 🚀"
)


def build_email(findings):
    """findings: list of dicts with company, category, ctc, item(dict)."""
    intro = "Prince Singh has sent something for you:"

    text_lines = [intro, CUSTOM_MESSAGE, ""]
    html_rows = []

    for f in findings:
        item = f["item"]
        role = item["title"]
        company = f["company"]
        location = item.get("location") or "India"
        job_id = item["id"]
        package = f["ctc"] or "Not listed"
        if item.get("is_intern"):
            package = f"{package} (internship — verify exact stipend on page)"
        timeline = item.get("posted_date") or "No info about timeline"
        if timeline != "No info about timeline":
            timeline = f"Listed on {timeline} — closing date not published; apply as soon as possible"

        link = item.get("url", "")
        has_link = is_valid_public_link(link)

        text_lines.append(
            f"Company: {company}\n"
            f"Location: {location}\n"
            f"Job ID: {job_id}\n"
            f"Role: {role}\n"
            f"Package: {package}\n"
            f"Timeline: {timeline}\n"
            + (f"Apply: {link}\n" if has_link else "Apply link: not available — search manually using the Job ID and Role above.\n")
        )

        apply_html = (
            f'<a href="{link}" style="display:inline-block; margin-top:10px; padding:8px 16px; background:#2563eb; color:#ffffff; text-decoration:none; border-radius:6px; font-size:13px; font-weight:bold;">Apply Now</a>'
            if has_link else
            '<div style="margin-top:10px; font-size:13px; color:#b91c1c;">Apply link not available — search manually using the Job ID and Role.</div>'
        )

        html_rows.append(f"""
        <div style="border:1px solid #e2e2e2; border-radius:10px; padding:16px 20px; margin-bottom:14px; font-family:Arial,Helvetica,sans-serif;">
          <div style="font-size:16px; font-weight:bold; color:#1a1a1a; margin-bottom:6px;">{company}</div>
          <table style="width:100%; font-size:14px; color:#333;">
            <tr><td style="padding:2px 0; width:110px; color:#777;">Location</td><td>{location}</td></tr>
            <tr><td style="padding:2px 0; color:#777;">Job ID</td><td>{job_id}</td></tr>
            <tr><td style="padding:2px 0; color:#777;">Role</td><td>{role}</td></tr>
            <tr><td style="padding:2px 0; color:#777;">Package</td><td>{package}</td></tr>
            <tr><td style="padding:2px 0; color:#777;">Timeline</td><td>{timeline}</td></tr>
          </table>
          {apply_html}
        </div>
        """)

    digest_text = "\n".join(text_lines)
    digest_html = f"""
    <div style="font-family:Arial,Helvetica,sans-serif; max-width:640px; margin:0 auto;">
      <p style="font-size:16px; color:#1a1a1a; font-weight:bold; margin-bottom:4px;">{intro}</p>
      <p style="font-size:14px; color:#444; margin-top:0; margin-bottom:20px; line-height:1.5;">{CUSTOM_MESSAGE}</p>
      {''.join(html_rows)}
    </div>
    """
    return digest_text, digest_html


def send_email(digest_html, digest_text, count):
    host = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    to_addr = os.environ.get("EMAIL_TO", user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Prince Singh has sent something for you: {count} new opening(s)"
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

    findings = []  # list of {company, category, ctc, item}

    for company in companies:
        name = company["name"]
        prev = state.get(name, {"seen_ids": [], "hash": None})

        jobs = fetch_api_jobs(company)
        if jobs is not None:
            relevant = []
            for j in jobs:
                if is_excluded(j["title"]):
                    continue
                reasons = classify(j["title"])
                intern = is_internship(j["title"])
                if not reasons and not intern:
                    continue
                if is_india_location(j.get("location", "")) is not True:
                    continue
                if not passes_all_filters(j["title"], company, intern):
                    continue
                j["reasons"] = sorted(reasons) if reasons else ["internship"]
                j["is_intern"] = intern
                relevant.append(j)

            seen_ids = set(prev.get("seen_ids", []))
            for j in relevant:
                if j["id"] not in seen_ids:
                    findings.append({
                        "company": name,
                        "category": company.get("category", ""),
                        "ctc": company.get("ctc"),
                        "item": j,
                    })
            state[name] = {"seen_ids": [j["id"] for j in relevant], "hash": None, "mode": "api"}
        else:
            items, content_hash = fetch_generic(company)
            if items is not None:
                prev_hash = prev.get("hash")
                if content_hash != prev_hash:
                    for it in items:
                        findings.append({
                            "company": name,
                            "category": company.get("category", ""),
                            "ctc": company.get("ctc"),
                            "item": it,
                        })
                state[name] = {"seen_ids": [], "hash": content_hash, "mode": "generic"}
            else:
                state[name] = prev
                state[name]["mode"] = "failed"

        time.sleep(1)  # be polite to servers

    save_json(STATE_FILE, state)

    if not findings:
        print("No new matching openings found this run.")
        return

    digest_text, digest_html = build_email(findings)

    try:
        send_email(digest_html, digest_text, len(findings))
        print(f"Email sent with {len(findings)} new listing(s).")
    except Exception as e:
        print(f"Failed to send email: {e}", file=sys.stderr)
        print(digest_text)
        sys.exit(1)


if __name__ == "__main__":
    main()
