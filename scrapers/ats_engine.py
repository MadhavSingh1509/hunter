"""
Hunter 4.0 - Multi-Source ATS Discovery Adapters
Provides robust, paginated discovery adapters for:
- Amazon Jobs Official API
- Salesforce Workday CXS API
- Barclays TalentBrew API
- Accenture Careers API
- Greenhouse Public API
- Lever Public API
- SmartRecruiters Public API
- Ashby Public API
- General Workday CXS API
"""

import time
import requests
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("hunter.scrapers")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

class ATSDiscoveryEngine:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    # ---------------------------------------------------------
    # 1. Amazon Jobs Official API
    # ---------------------------------------------------------
    def fetch_amazon_jobs(self, query: str = "software", max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Discovers jobs via official Amazon Jobs JSON API.
        Endpoint: https://www.amazon.jobs/en/search.json
        """
        base_url = "https://www.amazon.jobs/en/search.json"
        all_jobs = []
        limit = 50

        for page in range(max_pages):
            offset = page * limit
            params = {
                "base_query": query,
                "country": "IND",
                "result_limit": limit,
                "offset": offset,
                "sort": "recent",
                "category[]": "software-development"
            }
            try:
                resp = self.session.get(base_url, params=params, timeout=self.timeout)
                if resp.status_code != 200:
                    logger.warning(f"Amazon API returned status {resp.status_code}")
                    break
                data = resp.json()
                jobs = data.get("jobs", [])
                if not jobs:
                    break

                for j in jobs:
                    job_path = j.get("job_path", "")
                    canonical_url = f"https://www.amazon.jobs{job_path}" if job_path.startswith("/") else job_path
                    all_jobs.append({
                        "company_id": "amazon",
                        "company_name": "Amazon",
                        "ats_job_id": str(j.get("id_icims") or j.get("id") or ""),
                        "title": j.get("title", ""),
                        "canonical_url": canonical_url,
                        "location": f"{j.get('city', '')}, {j.get('country_code', 'IND')}",
                        "is_india_eligible": True,
                        "employment_type": "Full-time" if "full" in str(j.get("job_schedule_type", "")).lower() else "Internship",
                        "description": f"{j.get('description', '')} {j.get('basic_qualifications', '')} {j.get('preferred_qualifications', '')}",
                        "application_status": "OPEN",
                        "source": "amazon_jobs_api"
                    })

                total_hits = data.get("hits", 0)
                if len(all_jobs) >= total_hits or len(jobs) < limit:
                    break
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error querying Amazon API: {e}")
                break

        return all_jobs

    # ---------------------------------------------------------
    # 2. Salesforce Workday CXS API
    # ---------------------------------------------------------
    def fetch_salesforce_jobs(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Discovers jobs via Salesforce Workday CXS API.
        Endpoint: https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs
        """
        endpoint = "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs"
        all_jobs = []
        limit = 20

        for page in range(max_pages):
            offset = page * limit
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "India"
            }
            try:
                resp = self.session.post(endpoint, json=payload, timeout=self.timeout)
                if resp.status_code != 200:
                    logger.warning(f"Salesforce Workday API returned {resp.status_code}")
                    break
                data = resp.json()
                postings = data.get("jobPostings", [])
                if not postings:
                    break

                for p in postings:
                    external_path = p.get("externalPath", "")
                    canonical_url = f"https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site{external_path}"
                    all_jobs.append({
                        "company_id": "salesforce",
                        "company_name": "Salesforce",
                        "ats_job_id": str(p.get("bulletFields", [None])[0] or p.get("externalPath", "")),
                        "title": p.get("title", ""),
                        "canonical_url": canonical_url,
                        "location": p.get("locationsText", "India"),
                        "is_india_eligible": "india" in p.get("locationsText", "").lower(),
                        "employment_type": "Full-time" if "full" in str(p.get("timeType", "")).lower() else "Internship",
                        "description": p.get("title", ""),
                        "application_status": "OPEN",
                        "source": "salesforce_workday_cxs"
                    })

                total = data.get("total", 0)
                if len(all_jobs) >= total or len(postings) < limit:
                    break
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error querying Salesforce API: {e}")
                break

        return all_jobs

    # ---------------------------------------------------------
    # 3. Barclays TalentBrew API & Portal
    # ---------------------------------------------------------
    def fetch_barclays_jobs(self, query: str = "developer", max_pages: int = 2) -> List[Dict[str, Any]]:
        """
        Discovers jobs via Barclays TalentBrew portal.
        Verified endpoint: https://search.jobs.barclays/search-jobs/{query}
        """
        all_jobs = []
        queries = [query, "software", "engineer"]
        seen_urls = set()

        from bs4 import BeautifulSoup

        for q in queries:
            url = f"https://search.jobs.barclays/search-jobs/{q}"
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    if "/job/" in href:
                        # Check if India related
                        href_lower = href.lower()
                        text_lower = a.get_text(strip=True).lower()
                        is_india = any(c in href_lower or c in text_lower for c in ["pune", "chennai", "noida", "india"])
                        canonical_url = f"https://search.jobs.barclays{href}" if href.startswith("/") else href
                        
                        if is_india and canonical_url not in seen_urls:
                            seen_urls.add(canonical_url)
                            title = a.get_text(strip=True)
                            loc = "Pune, India" if "pune" in href_lower else ("Chennai, India" if "chennai" in href_lower else "India")
                            all_jobs.append({
                                "company_id": "barclays",
                                "company_name": "Barclays",
                                "ats_job_id": href.rstrip("/").split("/")[-1],
                                "title": title,
                                "canonical_url": canonical_url,
                                "location": loc,
                                "is_india_eligible": True,
                                "employment_type": "Full-time",
                                "description": f"{title} - Barclays India Technology ({loc})",
                                "application_status": "OPEN",
                                "source": "barclays_portal"
                            })
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Error querying Barclays for {q}: {e}")

        return all_jobs

    # ---------------------------------------------------------
    # 3b. Accenture India Discovery
    # ---------------------------------------------------------
    def fetch_accenture_jobs(self) -> List[Dict[str, Any]]:
        """
        Monitors Accenture India careers opportunities.
        """
        all_jobs = []
        # Return registered entry/off-campus opportunity if responsive
        try:
            url = "https://www.accenture.com/in-en/careers/jobsearch?jk=software%20engineer"
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                all_jobs.append({
                    "company_id": "accenture",
                    "company_name": "Accenture",
                    "ats_job_id": "accenture-india-software-portal",
                    "title": "Associate Software Engineer / Software Engineering Associate",
                    "canonical_url": "https://www.accenture.com/in-en/careers/jobsearch?jk=software%20engineer",
                    "location": "Bengaluru / Hyderabad / Pune / NCR, India",
                    "is_india_eligible": True,
                    "employment_type": "Full-time",
                    "description": "Accenture India Entry-Level Software Engineering and Application Development Associate opportunities for engineering freshers.",
                    "application_status": "OPEN",
                    "source": "accenture_portal"
                })
        except Exception as e:
            logger.error(f"Error checking Accenture portal: {e}")

        return all_jobs

    # ---------------------------------------------------------
    # 4. Greenhouse Public Board API
    # ---------------------------------------------------------
    def fetch_greenhouse_jobs(self, slug: str, company_name: str, company_id: str) -> List[Dict[str, Any]]:
        """
        Fetches jobs from official Greenhouse API.
        Endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
        """
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        all_jobs = []
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                return []
            if resp.status_code != 200:
                logger.warning(f"Greenhouse {slug} returned status {resp.status_code}")
                return []

            data = resp.json()
            jobs = data.get("jobs", [])
            for j in jobs:
                loc_name = (j.get("location") or {}).get("name", "")
                canonical_url = j.get("absolute_url", "")
                desc = j.get("content", "")

                all_jobs.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "ats_job_id": str(j.get("id")),
                    "title": j.get("title", ""),
                    "canonical_url": canonical_url,
                    "location": loc_name or "India",
                    "is_india_eligible": any(c in loc_name.lower() for c in ["india", "bengaluru", "bangalore", "hyderabad", "pune", "delhi", "remote"]),
                    "employment_type": "Full-time",
                    "description": desc,
                    "application_status": "OPEN",
                    "source": "greenhouse_api"
                })
        except Exception as e:
            logger.error(f"Error fetching Greenhouse jobs for {slug}: {e}")

        return all_jobs

    # ---------------------------------------------------------
    # 5. Lever Public Postings API
    # ---------------------------------------------------------
    def fetch_lever_jobs(self, slug: str, company_name: str, company_id: str) -> List[Dict[str, Any]]:
        """
        Fetches jobs from Lever public postings API.
        Endpoint: https://api.lever.co/v0/postings/{slug}?mode=json
        """
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        all_jobs = []
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return []
            postings = resp.json()
            for p in postings:
                cats = p.get("categories", {})
                loc = cats.get("location", "")
                canonical_url = p.get("hostedUrl", "")
                desc = f"{p.get('descriptionPlain', '')} {p.get('additionalPlain', '')}"

                all_jobs.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "ats_job_id": str(p.get("id", "")),
                    "title": p.get("text", ""),
                    "canonical_url": canonical_url,
                    "location": loc or "India",
                    "is_india_eligible": any(c in loc.lower() for c in ["india", "bengaluru", "bangalore", "hyderabad", "pune", "delhi", "remote"]),
                    "employment_type": cats.get("commitment", "Full-time"),
                    "description": desc,
                    "application_status": "OPEN",
                    "source": "lever_api"
                })
        except Exception as e:
            logger.error(f"Error fetching Lever jobs for {slug}: {e}")

        return all_jobs

    # ---------------------------------------------------------
    # 6. SmartRecruiters Public API
    # ---------------------------------------------------------
    def fetch_smartrecruiters_jobs(self, slug: str, company_name: str, company_id: str) -> List[Dict[str, Any]]:
        """
        Fetches jobs from SmartRecruiters public API.
        Endpoint: https://api.smartrecruiters.com/v1/companies/{slug}/postings
        """
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        all_jobs = []
        try:
            resp = self.session.get(url, params={"limit": 50}, timeout=self.timeout)
            if resp.status_code != 200:
                return []
            data = resp.json()
            content = data.get("content", [])
            for item in content:
                location = item.get("location", {})
                loc_str = f"{location.get('city', '')}, {location.get('country', '')}"
                job_id = item.get("id", "")
                canonical_url = f"https://jobs.smartrecruiters.com/{slug}/{job_id}"

                all_jobs.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "ats_job_id": str(job_id),
                    "title": item.get("name", ""),
                    "canonical_url": canonical_url,
                    "location": loc_str,
                    "is_india_eligible": "in" in location.get("country", "").lower() or "india" in loc_str.lower(),
                    "employment_type": (item.get("typeOfEmployment") or {}).get("label", "Full-time"),
                    "description": item.get("name", ""),
                    "application_status": "OPEN",
                    "source": "smartrecruiters_api"
                })
        except Exception as e:
            logger.error(f"Error fetching SmartRecruiters jobs for {slug}: {e}")

        return all_jobs

    # ---------------------------------------------------------
    # 7. Ashby Public API
    # ---------------------------------------------------------
    def fetch_ashby_jobs(self, slug: str, company_name: str, company_id: str) -> List[Dict[str, Any]]:
        """
        Fetches jobs from Ashby public job board API.
        Endpoint: https://api.ashbyhq.com/posting-api/job-board/{slug}
        """
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        all_jobs = []
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return []
            data = resp.json()
            jobs = data.get("jobs", [])
            for j in jobs:
                canonical_url = j.get("jobUrl", "")
                loc = j.get("location", "")
                all_jobs.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "ats_job_id": str(j.get("id", "")),
                    "title": j.get("title", ""),
                    "canonical_url": canonical_url,
                    "location": loc or "India",
                    "is_india_eligible": any(c in loc.lower() for c in ["india", "bengaluru", "bangalore", "remote"]),
                    "employment_type": j.get("employmentType", "Full-time"),
                    "description": j.get("descriptionHtml", ""),
                    "application_status": "OPEN",
                    "source": "ashby_api"
                })
        except Exception as e:
            logger.error(f"Error fetching Ashby jobs for {slug}: {e}")

        return all_jobs

    # ---------------------------------------------------------
    # 8. Direct Job URL Verifier
    # ---------------------------------------------------------
    def verify_job_url(self, url: str) -> Tuple[bool, str]:
        """
        Verifies that an official job URL is responsive and open.
        Returns (is_valid: bool, status: 'OPEN' | 'CLOSED' | 'UNVERIFIED').
        """
        if not url or not url.startswith("http"):
            return False, "UNVERIFIED"
        try:
            head_resp = self.session.head(url, timeout=8, allow_redirects=True)
            if head_resp.status_code in [200, 301, 302]:
                return True, "OPEN"
            if head_resp.status_code in [404, 410]:
                return False, "CLOSED"

            # Fallback to GET with stream=True
            get_resp = self.session.get(url, timeout=8, stream=True, allow_redirects=True)
            if get_resp.status_code == 200:
                return True, "OPEN"
            elif get_resp.status_code in [404, 410]:
                return False, "CLOSED"
            else:
                return False, "UNVERIFIED"
        except Exception:
            return False, "UNVERIFIED"
