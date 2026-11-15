"""
Hunter 2.0 ATS Providers
Connects to official ATS platforms (Greenhouse, Lever, SmartRecruiters, Ashby)
and retrieves verified job openings with their full job descriptions and direct application URLs.
"""

import re
import html
import time
import requests
from typing import List, Dict, Any, Optional
from qualification_engine import JobPosting

REQUEST_TIMEOUT = 12


def clean_html(raw_html: str) -> str:
    """Removes HTML tags and normalizes whitespace."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    return " ".join(text.split())


class ATSProvider:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "HunterJobBot/2.0 (+https://github.com/MadhavSingh1509/hunter)"
        })

    def fetch_greenhouse(self, company_name: str, slug: str) -> List[JobPosting]:
        """
        Fetches job listings from Greenhouse API including full job descriptions.
        Optimized to fetch full description only for candidate roles in India.
        """
        list_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            r = self.session.get(list_url, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                return []
            data = r.json()
            raw_jobs = data.get("jobs", [])
            postings = []

            # Fast preliminary check keywords
            skip_title_cues = ["senior", "sr.", "sr ", "staff", "principal", "lead ", "manager", "director", "architect", "vp,", "head of", "sales", "recruiter", "hr "]
            foreign_cues = ["usa", "united states", "san francisco", "seattle", "new york", "austin", "london", "singapore", "germany", "canada", "sydney"]

            for rj in raw_jobs:
                job_id = str(rj.get("id", ""))
                title = rj.get("title", "")
                url = rj.get("absolute_url", "")
                loc = (rj.get("location") or {}).get("name", "")
                posted_date = (rj.get("updated_at") or "")[:10]

                t_lower = title.lower()
                loc_lower = loc.lower()

                # Determine if deep description fetch is warranted
                is_obviously_skipped = any(cue in t_lower for cue in skip_title_cues) or \
                    (any(fc in loc_lower for fc in foreign_cues) and "india" not in loc_lower)

                desc_text = ""
                if not is_obviously_skipped:
                    try:
                        detail_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"
                        dr = self.session.get(detail_url, timeout=REQUEST_TIMEOUT)
                        if dr.status_code == 200:
                            detail = dr.json()
                            desc_text = clean_html(detail.get("content", ""))
                    except Exception:
                        desc_text = ""

                postings.append(JobPosting(
                    company=company_name,
                    title=title,
                    url=url,
                    location=loc,
                    description=desc_text,
                    job_id=f"gh-{job_id}",
                    posted_date=posted_date,
                    raw_data=rj
                ))
            return postings
        except Exception:
            return []

    def fetch_lever(self, company_name: str, slug: str) -> List[JobPosting]:
        """
        Fetches job listings from Lever API with full plain text descriptions and requirement lists.
        """
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                return []
            data = r.json()
            if not isinstance(data, list):
                return []

            postings = []
            for j in data:
                job_id = j.get("id", "")
                title = j.get("text", "")
                apply_url = j.get("hostedUrl", "")
                loc = (j.get("categories") or {}).get("location", "")
                
                # Combine description and requirement lists
                desc_plain = j.get("descriptionPlain", "")
                lists = j.get("lists", [])
                lists_text = ""
                if isinstance(lists, list):
                    for item in lists:
                        header = item.get("text", "")
                        content = clean_html(item.get("content", ""))
                        lists_text += f"\n{header}:\n{content}"

                full_desc = f"{desc_plain}\n{lists_text}".strip()

                created_ms = j.get("createdAt")
                posted_date = ""
                if created_ms:
                    try:
                        posted_date = time.strftime("%Y-%m-%d", time.gmtime(created_ms / 1000))
                    except Exception:
                        posted_date = ""

                postings.append(JobPosting(
                    company=company_name,
                    title=title,
                    url=apply_url,
                    location=loc,
                    description=full_desc,
                    job_id=f"lever-{job_id}",
                    posted_date=posted_date,
                    raw_data=j
                ))
            return postings
        except Exception:
            return []

    def fetch_smartrecruiters(self, company_name: str, slug: str) -> List[JobPosting]:
        """
        Fetches job postings from SmartRecruiters API and retrieves full qualification details and apply URLs.
        """
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                return []
            data = r.json()
            content = data.get("content", [])
            postings = []

            for item in content:
                job_id = str(item.get("id", ""))
                title = item.get("name", "")
                loc_obj = item.get("location") or {}
                loc_str = ", ".join(
                    str(v) for v in (loc_obj.get("city"), loc_obj.get("region"), loc_obj.get("country")) if v
                )
                posted_date = (item.get("releasedDate") or "")[:10]

                # Resolve detailed application URL and description
                public_url = ""
                desc_text = ""
                ref_url = item.get("ref", "")
                if ref_url:
                    try:
                        detail_resp = self.session.get(ref_url, timeout=REQUEST_TIMEOUT)
                        if detail_resp.status_code == 200:
                            detail = detail_resp.json()
                            public_url = detail.get("applyUrl") or detail.get("postingUrl") or ""
                            sections = (detail.get("jobAd") or {}).get("sections") or {}
                            desc_parts = []
                            for sec_name, sec_val in sections.items():
                                if isinstance(sec_val, dict):
                                    t = clean_html(sec_val.get("text", ""))
                                    if t:
                                        desc_parts.append(f"{sec_name}: {t}")
                            desc_text = "\n".join(desc_parts)
                    except Exception:
                        pass

                # If public apply URL is missing, construct the canonical job posting page
                if not public_url:
                    public_url = f"https://jobs.smartrecruiters.com/{slug}/{job_id}"

                postings.append(JobPosting(
                    company=company_name,
                    title=title,
                    url=public_url,
                    location=loc_str,
                    description=desc_text,
                    job_id=f"sr-{job_id}",
                    posted_date=posted_date,
                    raw_data=item
                ))
            return postings
        except Exception:
            return []

    def fetch_ashby(self, company_name: str, slug: str) -> List[JobPosting]:
        """
        Fetches job postings from Ashby API.
        """
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                return []
            data = r.json()
            jobs = data.get("jobs", [])
            postings = []
            for j in jobs:
                job_id = str(j.get("id", ""))
                title = j.get("title", "")
                apply_url = j.get("applyUrl") or j.get("jobUrl") or ""
                loc = j.get("location", "")
                desc = clean_html(j.get("descriptionHtml") or j.get("descriptionPlain") or "")
                postings.append(JobPosting(
                    company=company_name,
                    title=title,
                    url=apply_url,
                    location=loc,
                    description=desc,
                    job_id=f"ashby-{job_id}",
                    posted_date=(j.get("publishedAt") or "")[:10],
                    raw_data=j
                ))
            return postings
        except Exception:
            return []
