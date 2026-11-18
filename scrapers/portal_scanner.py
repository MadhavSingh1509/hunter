"""
Hunter — Multi-ATS Portal Scanner (Complete Pagination + Individual JD Fetching + Posting Date Extraction)
Searches all 71 watchlist companies using their verified official career portals and ATS endpoints:
- Workday CXS (paginated search + individual job description & postedOn detail fetch)
- Oracle Cloud HCM (paginated search + individual requisition detail fetch)
- Greenhouse (full content JSON API)
- Lever (full JSON API)
- SmartRecruiters (paginated search + individual posting detail fetch)
- Eightfold AI PCSX (paginated search + individual position detail fetch)
- Amazon Jobs Official JSON API (paginated + full qualifications)
- Atlassian Official JSON API (full descriptions)
- AMD Jibe Official JSON API (paginated + full descriptions)
- Google Careers (paginated India search + individual job page JD fetch)
- TalentBrew (Barclays, Intuit, Synopsys, Palo Alto fallback + individual job page JD fetch)
- Apple / Uber / Goldman Sachs / Generic Official Career Portals (with retry & explicit failure tracking)
"""

import re
import time
import html
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin

from core.fresher_filter import StrictFresherFilter

logger = logging.getLogger("hunter.scanner")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, application/xhtml+xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class CompanyScanReport:
    company: str
    scanner_type: str
    status: str  # "SCANNED_OK" | "PARTIAL" | "FAILED"
    total_retrieved: int = 0
    candidate_jds_checked: int = 0
    fresher_matches: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""


def format_posted_date(raw_val: Any) -> str:
    """
    Normalizes an original posting date into 'DD Mon YYYY' (e.g. '17 Nov 2026').
    Never fabricates a date. Returns 'Not disclosed' if unavailable.
    """
    if raw_val is None:
        return "Not disclosed"

    # Epoch timestamp (seconds or milliseconds)
    if isinstance(raw_val, (int, float)) and raw_val > 0:
        try:
            ts = raw_val / 1000.0 if raw_val > 1e11 else float(raw_val)
            dt = datetime.utcfromtimestamp(ts)
            return dt.strftime("%d %b %Y")
        except Exception:
            return "Not disclosed"

    s = str(raw_val).strip()
    if not s:
        return "Not disclosed"

    s_lower = s.lower()

    # Workday relative strings
    if "posted today" in s_lower or s_lower == "today":
        return datetime.utcnow().strftime("%d %b %Y")
    if "posted yesterday" in s_lower or s_lower == "yesterday":
        return (datetime.utcnow() - timedelta(days=1)).strftime("%d %b %Y")
    m_days = re.search(r"posted\s+(\d+)\s+days?\s+ago", s_lower)
    if m_days:
        days = int(m_days.group(1))
        return (datetime.utcnow() - timedelta(days=days)).strftime("%d %b %Y")
    if "30+ days ago" in s_lower:
        return "30+ days ago"

    # ISO 8601 date prefix: YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m_iso:
        try:
            dt = datetime(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
            return dt.strftime("%d %b %Y")
        except Exception:
            pass

    # Common textual dates: "November 17, 2026", "Nov 17, 2026", "17 Nov 2026", "11/17/2026"
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %b %Y", "%d %B %Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(s[:25].strip(), fmt)
            return dt.strftime("%d %b %Y")
        except Exception:
            continue

    return "Not disclosed"


class PortalScanner:
    def __init__(self, fresher_filter: StrictFresherFilter, timeout: int = 12):
        self.filter = fresher_filter
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _request(self, method: str, url: str, retries: int = 2, **kwargs) -> Optional[requests.Response]:
        """HTTP request with polite retry on transient 429/5xx/timeouts."""
        kwargs.setdefault("timeout", (6, self.timeout))
        for attempt in range(retries + 1):
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code == 429:
                    if attempt < retries:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    return resp
                if resp.status_code >= 500 and attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return resp
            except requests.RequestException:
                if attempt < retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                return None
        return None

    def verify_application_url(self, url: str) -> bool:
        """
        Verifies the official job application URL is live and not closed/404.
        Rejects generic careers homepages.
        """
        if not url or not url.startswith("http"):
            return False
        # Reject generic careers root pages with no job identifier
        path_only = url.split("?")[0].rstrip("/")
        if re.search(r"/(?:careers|jobs|jobsearch|open-positions)$", path_only.lower()) and "?" not in url:
            return False

        # For API-sourced canonical URLs, do a lightweight HEAD/GET check
        resp = self._request("HEAD", url, retries=1, allow_redirects=True, timeout=(5, 8))
        if resp is not None:
            if resp.status_code in (200, 301, 302, 303, 307, 308):
                return True
            if resp.status_code in (404, 410):
                return False
            # Some ATS portals reject HEAD with 403/405 -> try streamed GET
            if resp.status_code in (403, 405):
                r2 = self._request("GET", url, retries=0, allow_redirects=True, stream=True, timeout=(5, 8))
                if r2 is not None:
                    if r2.status_code in (404, 410):
                        return False
                    # 200 or 403 bot-wall on known valid ATS API link -> accept if API returned it as OPEN
                    return r2.status_code in (200, 403)
        return True

    def _preliminary_check(self, title: str, location: str) -> bool:
        """Fast pre-filter before fetching individual JD pages (Role Title + India Location)."""
        role_ok, _ = self.filter.check_role(title)
        if not role_ok:
            return False
        # Allow unknown/empty location through to JD check only if not explicitly foreign
        loc_lower = (location or "").lower()
        for f in self.filter.FOREIGN_LOCATIONS:
            if re.search(rf"\b{re.escape(f)}\b", loc_lower):
                # Unless an India city is ALSO present (multi-location posting)
                if not any(re.search(rf"\b{re.escape(c)}\b", loc_lower) for c in self.filter.INDIA_LOCATIONS):
                    return False
        return True

    # =========================================================================
    # 1. WORKDAY CXS ADAPTER (Full Pagination + Individual JD Detail Fetch)
    # =========================================================================
    def scan_workday(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        host = cfg["host"]
        tenant = cfg["tenant"]
        sites = cfg.get("sites", ["External"])
        prefix = cfg.get("query_prefix", "")
        report = CompanyScanReport(company=company, scanner_type="workday", status="SCANNED_OK")

        seen_paths = set()
        raw_postings = []
        any_success = False
        last_err = ""

        # Search queries to ensure full India fresher coverage even on large boards
        queries = [f"{prefix} India".strip(), f"{prefix} India intern".strip(), f"{prefix} India graduate".strip()]
        if prefix:
            queries = [f"{prefix} India"]

        for site in sites:
            api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
            for q in queries:
                offset = 0
                limit = 20
                known_total = None
                max_pages = 25  # Up to 500 listings per query
                for page in range(max_pages):
                    payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": q}
                    resp = self._request(
                        "POST", api_url,
                        json=payload,
                        headers={**DEFAULT_HEADERS, "Content-Type": "application/json", "Origin": f"https://{host}"}
                    )
                    if resp is None:
                        last_err = "Connection timeout/error"
                        break
                    if resp.status_code != 200:
                        last_err = f"HTTP {resp.status_code}"
                        break

                    any_success = True
                    data = resp.json()
                    postings = data.get("jobPostings", [])
                    # Workday CXS only returns non-zero 'total' on offset=0; preserve known_total across pages!
                    page_total = data.get("total", 0)
                    if page_total and page_total > 0:
                        known_total = page_total
                    if not postings:
                        break

                    for p in postings:
                        ext_path = p.get("externalPath", "")
                        if ext_path and ext_path not in seen_paths:
                            seen_paths.add(ext_path)
                            raw_postings.append((site, p))

                    offset += limit
                    if len(postings) < limit:
                        break
                    if known_total is not None and offset >= known_total:
                        break
                    time.sleep(0.2)

                # If broad "India" query already covered all jobs (< 480), skip redundant sub-queries
                if q == queries[0] and known_total is not None and known_total < 480:
                    break

        if not any_success:
            # Check if a TalentBrew fallback is configured (e.g. Palo Alto Networks)
            if cfg.get("fallback_talentbrew"):
                fb_url = cfg["fallback_talentbrew"]
                base = "/".join(fb_url.split("/")[:3])
                path = "/" + "/".join(fb_url.split("/")[3:])
                return self.scan_talentbrew(company, {"base_url": base, "search_paths": [path]})
            report.status = "FAILED"
            report.error = f"Workday API unreachable ({last_err})"
            return report

        report.total_retrieved = len(raw_postings)

        # Pre-filter candidates and fetch individual full JDs
        for site, p in raw_postings:
            title = p.get("title", "")
            loc = p.get("locationsText", "")
            ext_path = p.get("externalPath", "")
            if not self._preliminary_check(title, loc):
                continue

            # Fetch individual job details from Workday CXS
            detail_url = f"https://{host}/wday/cxs/{tenant}/{site}{ext_path}"
            report.candidate_jds_checked += 1
            d_resp = self._request("GET", detail_url)
            description = ""
            posted_raw = p.get("postedOn", "")
            canonical_url = f"https://{host}/en-US/{site}{ext_path}"
            job_id = str((p.get("bulletFields") or [ext_path])[0])

            if d_resp is not None and d_resp.status_code == 200:
                info = d_resp.json().get("jobPostingInfo", {})
                description = info.get("jobDescription", "") or ""
                if info.get("startDate"):
                    posted_raw = info.get("startDate")
                elif info.get("postedOn"):
                    posted_raw = info.get("postedOn")
                if info.get("externalUrl"):
                    canonical_url = info.get("externalUrl")
                if info.get("location"):
                    loc = f"{loc} {info.get('location')}"
                if info.get("additionalLocations"):
                    loc = f"{loc} {' '.join(info.get('additionalLocations', []))}"
                if info.get("jobReqId"):
                    job_id = str(info.get("jobReqId"))

            decision = self.filter.evaluate(title, loc, description)
            if decision.is_eligible:
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": job_id,
                    "title": title.strip(),
                    "location": loc.strip(),
                    "posted_on": format_posted_date(posted_raw),
                    "canonical_url": canonical_url,
                    "reason": decision.reason,
                })
            time.sleep(0.15)

        return report

    # =========================================================================
    # 2. ORACLE CLOUD HCM ADAPTER (Pagination + Individual Requisition Details)
    # =========================================================================
    def scan_oracle_hcm(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        host = cfg["host"]
        site = cfg["site"]
        report = CompanyScanReport(company=company, scanner_type="oracle_hcm", status="SCANNED_OK")

        seen_ids = set()
        raw_reqs = []
        any_success = False
        last_err = ""

        # Search India-focused & fresher keywords so India roles aren't buried behind US listings
        keywords = ["India", "India%20Software", "India%20Intern", "India%20Graduate", "Intern", "Graduate"]
        for kw in keywords:
            offset = 0
            limit = 25
            for page in range(10):  # Up to 250 per keyword
                url = (
                    f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                    f"?onlyData=true&expand=requisitionList.secondaryLocations"
                    f"&finder=findReqs;siteNumber={site},limit={limit},offset={offset},keyword={kw}"
                )
                resp = self._request("GET", url)
                if resp is None:
                    last_err = "Timeout/network error"
                    break
                if resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code}"
                    break

                any_success = True
                items = resp.json().get("items", [])
                if not items:
                    break
                reqs = items[0].get("requisitionList", [])
                total = items[0].get("TotalJobsCount", 0)
                if not reqs:
                    break

                for r in reqs:
                    rid = str(r.get("Id", ""))
                    if rid and rid not in seen_ids:
                        seen_ids.add(rid)
                        raw_reqs.append(r)

                offset += limit
                if offset >= total or len(reqs) < limit:
                    break
                time.sleep(0.2)

        if not any_success:
            report.status = "FAILED"
            report.error = f"Oracle HCM API unreachable ({last_err})"
            return report

        report.total_retrieved = len(raw_reqs)

        for r in raw_reqs:
            title = r.get("Title", "")
            prim_loc = r.get("PrimaryLocation", "") or ""
            sec_locs = " ".join(s.get("Name", "") for s in (r.get("secondaryLocations") or []))
            loc = f"{prim_loc} {sec_locs}".strip()
            rid = str(r.get("Id", ""))

            if not self._preliminary_check(title, loc):
                continue

            # Must be India location before fetching individual detail
            loc_ok, _ = self.filter.check_location(loc, title)
            if not loc_ok:
                continue

            # Fetch full requisition details
            detail_url = (
                f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
                f"?expand=all&onlyData=true&finder=ById;Id=%22{rid}%22,siteNumber={site}"
            )
            report.candidate_jds_checked += 1
            d_resp = self._request("GET", detail_url)
            description = f"{r.get('ShortDescriptionStr', '')}"
            posted_raw = r.get("PostedDate", "")

            if d_resp is not None and d_resp.status_code == 200:
                d_items = d_resp.json().get("items", [])
                if d_items:
                    det = d_items[0]
                    description = " ".join(filter(None, [
                        det.get("ShortDescriptionStr", ""),
                        det.get("ExternalDescriptionStr", ""),
                        det.get("ExternalQualificationsStr", ""),
                        det.get("ExternalResponsibilitiesStr", ""),
                    ]))
                    if det.get("ExternalPostedStartDate"):
                        posted_raw = det.get("ExternalPostedStartDate")

            decision = self.filter.evaluate(title, loc, description)
            if decision.is_eligible:
                apply_url = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{rid}"
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": rid,
                    "title": title.strip(),
                    "location": prim_loc.strip() or "India",
                    "posted_on": format_posted_date(posted_raw),
                    "canonical_url": apply_url,
                    "reason": decision.reason,
                })
            time.sleep(0.15)

        return report

    # =========================================================================
    # 3. GREENHOUSE ADAPTER (Full Content JSON API)
    # =========================================================================
    def scan_greenhouse(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        slug = cfg["slug"]
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        report = CompanyScanReport(company=company, scanner_type="greenhouse", status="SCANNED_OK")

        resp = self._request("GET", url)
        if resp is None or resp.status_code != 200:
            report.status = "FAILED"
            report.error = f"Greenhouse API error ({resp.status_code if resp else 'timeout'})"
            return report

        jobs = resp.json().get("jobs", [])
        report.total_retrieved = len(jobs)

        for j in jobs:
            title = j.get("title", "")
            loc = (j.get("location") or {}).get("name", "")
            if not self._preliminary_check(title, loc):
                continue

            report.candidate_jds_checked += 1
            desc = j.get("content", "") or ""
            posted_raw = j.get("first_published") or j.get("updated_at")

            decision = self.filter.evaluate(title, loc, desc)
            if decision.is_eligible:
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": str(j.get("id", "")),
                    "title": title.strip(),
                    "location": loc.strip(),
                    "posted_on": format_posted_date(posted_raw),
                    "canonical_url": j.get("absolute_url", ""),
                    "reason": decision.reason,
                })

        return report

    # =========================================================================
    # 4. LEVER ADAPTER (Full JSON API)
    # =========================================================================
    def scan_lever(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        slug = cfg["slug"]
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        report = CompanyScanReport(company=company, scanner_type="lever", status="SCANNED_OK")

        resp = self._request("GET", url)
        if resp is None or resp.status_code != 200:
            report.status = "FAILED"
            report.error = f"Lever API error ({resp.status_code if resp else 'timeout'})"
            return report

        postings = resp.json()
        if not isinstance(postings, list):
            report.status = "FAILED"
            report.error = "Unexpected Lever response format"
            return report

        report.total_retrieved = len(postings)

        for p in postings:
            title = p.get("text", "")
            cats = p.get("categories") or {}
            loc = cats.get("location", "") or ""
            all_locs = " ".join(cats.get("allLocations") or [])
            full_loc = f"{loc} {all_locs}".strip()

            if not self._preliminary_check(title, full_loc):
                continue

            report.candidate_jds_checked += 1
            lists_text = " ".join(
                f"{lst.get('text', '')} {lst.get('content', '')}"
                for lst in (p.get("lists") or [])
            )
            desc = f"{p.get('descriptionPlain', '')} {lists_text} {p.get('additionalPlain', '')}"
            posted_raw = p.get("createdAt")

            decision = self.filter.evaluate(title, full_loc, desc)
            if decision.is_eligible:
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": str(p.get("id", "")),
                    "title": title.strip(),
                    "location": loc.strip() or "India",
                    "posted_on": format_posted_date(posted_raw),
                    "canonical_url": p.get("hostedUrl", ""),
                    "reason": decision.reason,
                })

        return report

    # =========================================================================
    # 5. SMARTRECRUITERS ADAPTER (Full Pagination + Individual Posting Details)
    # =========================================================================
    def scan_smartrecruiters(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        slug = cfg["slug"]
        report = CompanyScanReport(company=company, scanner_type="smartrecruiters", status="SCANNED_OK")

        all_items = []
        offset = 0
        limit = 100
        any_success = False
        last_err = ""

        for page in range(15):
            url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
            resp = self._request("GET", url, params={"limit": limit, "offset": offset})
            if resp is None or resp.status_code != 200:
                last_err = f"HTTP {resp.status_code if resp else 'timeout'}"
                break
            any_success = True
            data = resp.json()
            content = data.get("content", [])
            total = data.get("totalFound", 0)
            if not content:
                break
            all_items.extend(content)
            offset += limit
            if offset >= total or len(content) < limit:
                break
            time.sleep(0.2)

        if not any_success:
            report.status = "FAILED"
            report.error = f"SmartRecruiters error ({last_err})"
            return report

        report.total_retrieved = len(all_items)

        for item in all_items:
            title = item.get("name", "")
            loc_obj = item.get("location") or {}
            country = str(loc_obj.get("country", "")).lower()
            city = str(loc_obj.get("city", ""))
            loc_str = f"{city}, {'India' if country == 'in' else country.upper()}".strip(", ")

            if not self._preliminary_check(title, loc_str):
                continue
            loc_ok, _ = self.filter.check_location(loc_str, title)
            if not loc_ok:
                continue

            # Fetch individual posting details for full JD
            jid = str(item.get("id", ""))
            det_url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings/{jid}"
            report.candidate_jds_checked += 1
            d_resp = self._request("GET", det_url)
            desc = ""
            apply_url = f"https://jobs.smartrecruiters.com/{slug}/{jid}"
            posted_raw = item.get("releasedDate")

            if d_resp is not None and d_resp.status_code == 200:
                det = d_resp.json()
                sections = (det.get("jobAd") or {}).get("sections") or {}
                desc = " ".join(
                    (sec.get("text", "") if isinstance(sec, dict) else "")
                    for sec in sections.values()
                )
                if det.get("applyUrl"):
                    apply_url = det.get("applyUrl")
                if det.get("releasedDate"):
                    posted_raw = det.get("releasedDate")

            decision = self.filter.evaluate(title, loc_str, desc)
            if decision.is_eligible:
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": jid,
                    "title": title.strip(),
                    "location": loc_str,
                    "posted_on": format_posted_date(posted_raw),
                    "canonical_url": apply_url,
                    "reason": decision.reason,
                })
            time.sleep(0.15)

        return report

    # =========================================================================
    # 6. EIGHTFOLD AI PCSX ADAPTER (Microsoft, Qualcomm, American Express)
    # =========================================================================
    def scan_eightfold_pcsx(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        host = cfg["host"]
        domain = cfg["domain"]
        report = CompanyScanReport(company=company, scanner_type="eightfold_pcsx", status="SCANNED_OK")

        seen_ids = set()
        raw_positions = []
        any_success = False
        last_err = ""

        queries = ["software", "intern", "university graduate", "fresher", "machine learning"]
        for q in queries:
            start = 0
            num = 10
            for page in range(12):  # Up to 120 per query
                url = f"https://{host}/api/pcsx/search"
                params = {"domain": domain, "query": q, "location": "India", "start": start, "num": num}
                resp = self._request("GET", url, params=params)
                if resp is None or resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code if resp else 'timeout'}"
                    break
                any_success = True
                data = resp.json().get("data", {})
                positions = data.get("positions", [])
                count = data.get("count", 0)
                if not positions:
                    break
                for pos in positions:
                    pid = str(pos.get("id", ""))
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        raw_positions.append(pos)
                start += num
                if start >= count or len(positions) < num:
                    break
                time.sleep(0.25)

        if not any_success:
            report.status = "FAILED"
            report.error = f"Eightfold PCSX API unreachable ({last_err})"
            return report

        report.total_retrieved = len(raw_positions)

        for pos in raw_positions:
            title = pos.get("name", "")
            locs = pos.get("locations") or [pos.get("location", "")]
            loc_str = ", ".join(str(x) for x in locs if x)

            if not self._preliminary_check(title, loc_str):
                continue
            loc_ok, _ = self.filter.check_location(loc_str, title)
            if not loc_ok:
                continue

            pid = str(pos.get("id", ""))
            report.candidate_jds_checked += 1
            det_url = f"https://{host}/api/pcsx/position_details"
            d_resp = self._request("GET", det_url, params={"position_id": pid, "domain": domain})
            desc = ""
            posted_raw = pos.get("postedTs") or pos.get("t_create")
            canonical_url = pos.get("positionUrl") or f"https://{host}/careers/job/{pid}"
            if canonical_url.startswith("/"):
                canonical_url = f"https://{host}{canonical_url}"

            if d_resp is not None and d_resp.status_code == 200:
                pdata = d_resp.json().get("data", {})
                desc = pdata.get("jobDescription", "") or ""
                if pdata.get("postedTs"):
                    posted_raw = pdata.get("postedTs")

            decision = self.filter.evaluate(title, loc_str, desc)
            if decision.is_eligible:
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": pid,
                    "title": title.strip(),
                    "location": loc_str,
                    "posted_on": format_posted_date(posted_raw),
                    "canonical_url": canonical_url,
                    "reason": decision.reason,
                })
            time.sleep(0.15)

        return report

    # =========================================================================
    # 7. AMAZON OFFICIAL JOBS JSON API (Full Pagination + Full Qualifications)
    # =========================================================================
    def scan_amazon(self, company: str) -> CompanyScanReport:
        report = CompanyScanReport(company=company, scanner_type="amazon_api", status="SCANNED_OK")
        base_url = "https://www.amazon.jobs/en/search.json"
        seen_ids = set()
        raw_jobs = []
        any_success = False
        last_err = ""

        # Explicitly query intern / graduate / university + general software so fresher roles are guaranteed to be found!
        queries = [
            {"base_query": "software development engineer intern", "country": "IND"},
            {"base_query": "software development engineer graduate", "country": "IND"},
            {"base_query": "software engineer", "country": "IND", "category[]": "software-development"},
            {"base_query": "machine learning intern", "country": "IND"},
        ]

        for qparams in queries:
            offset = 0
            limit = 50
            for page in range(6):  # Up to 300 per query
                params = {**qparams, "result_limit": limit, "offset": offset, "sort": "recent"}
                resp = self._request("GET", base_url, params=params)
                if resp is None or resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code if resp else 'timeout'}"
                    break
                any_success = True
                data = resp.json()
                jobs = data.get("jobs", [])
                hits = data.get("hits", 0)
                if not jobs:
                    break
                for j in jobs:
                    jid = str(j.get("id_icims") or j.get("id") or "")
                    if jid and jid not in seen_ids:
                        seen_ids.add(jid)
                        raw_jobs.append(j)
                offset += limit
                if offset >= hits or len(jobs) < limit:
                    break
                time.sleep(0.25)

        if not any_success:
            report.status = "FAILED"
            report.error = f"Amazon Jobs API error ({last_err})"
            return report

        report.total_retrieved = len(raw_jobs)

        for j in raw_jobs:
            title = j.get("title", "")
            loc = f"{j.get('city', '')}, {j.get('state', '')}, {j.get('country_code', 'IND')}".strip(", ")
            if not self._preliminary_check(title, loc):
                continue

            report.candidate_jds_checked += 1
            # Put basic_qualifications BEFORE preferred_qualifications so split_required_vs_preferred works accurately!
            desc = (
                f"{j.get('description', '')}\n"
                f"Basic Qualifications: {j.get('basic_qualifications', '')}\n"
                f"Preferred Qualifications: {j.get('preferred_qualifications', '')}"
            )
            decision = self.filter.evaluate(title, loc, desc)
            if decision.is_eligible:
                job_path = j.get("job_path", "")
                canonical_url = f"https://www.amazon.jobs{job_path}" if job_path.startswith("/") else job_path
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": str(j.get("id_icims") or j.get("id") or ""),
                    "title": title.strip(),
                    "location": loc,
                    "posted_on": format_posted_date(j.get("posted_date")),
                    "canonical_url": canonical_url,
                    "reason": decision.reason,
                })

        return report

    # =========================================================================
    # 8. ATLASSIAN OFFICIAL JSON API
    # =========================================================================
    def scan_atlassian(self, company: str) -> CompanyScanReport:
        url = "https://www.atlassian.com/endpoint/careers/listings"
        report = CompanyScanReport(company=company, scanner_type="atlassian_api", status="SCANNED_OK")

        resp = self._request("GET", url)
        if resp is None or resp.status_code != 200:
            report.status = "FAILED"
            report.error = f"Atlassian API error ({resp.status_code if resp else 'timeout'})"
            return report

        listings = resp.json()
        report.total_retrieved = len(listings)

        for item in listings:
            title = item.get("title", "")
            locs = item.get("locations") or []
            loc_str = ", ".join(locs) if isinstance(locs, list) else str(locs)
            if not self._preliminary_check(title, loc_str):
                continue

            report.candidate_jds_checked += 1
            desc = f"{item.get('overview', '')} {item.get('responsibilities', '')} {item.get('qualifications', '')}"
            decision = self.filter.evaluate(title, loc_str, desc)
            if decision.is_eligible:
                apply_url = item.get("applyUrl") or f"https://www.atlassian.com/company/careers/details/{item.get('id')}"
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": str(item.get("id", "")),
                    "title": title.strip(),
                    "location": loc_str,
                    "posted_on": format_posted_date(item.get("postedDate") or item.get("createdAt")),
                    "canonical_url": apply_url,
                    "reason": decision.reason,
                })

        return report

    # =========================================================================
    # 9. JIBE / iCIMS JSON API (AMD)
    # =========================================================================
    def scan_jibe(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        host = cfg["host"]
        report = CompanyScanReport(company=company, scanner_type="jibe_api", status="SCANNED_OK")

        seen_ids = set()
        raw_jobs = []
        any_success = False
        last_err = ""

        for kw in ["software", "intern", "graduate"]:
            for page in range(1, 15):
                url = f"https://{host}/api/jobs"
                params = {"keywords": kw, "location": "India", "page": page, "limit": 20}
                resp = self._request("GET", url, params=params)
                if resp is None or resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code if resp else 'timeout'}"
                    break
                any_success = True
                data = resp.json()
                jobs = data.get("jobs", [])
                if not jobs:
                    break
                for jwrap in jobs:
                    j = jwrap.get("data", jwrap)
                    jid = str(j.get("req_id") or j.get("slug") or "")
                    if jid and jid not in seen_ids:
                        seen_ids.add(jid)
                        raw_jobs.append(j)
                if len(jobs) < 20:
                    break
                time.sleep(0.2)

        if not any_success:
            report.status = "FAILED"
            report.error = f"Jibe API error ({last_err})"
            return report

        report.total_retrieved = len(raw_jobs)

        for j in raw_jobs:
            title = j.get("title", "")
            loc = j.get("full_location") or f"{j.get('city', '')}, {j.get('country', '')}"
            if not self._preliminary_check(title, loc):
                continue

            report.candidate_jds_checked += 1
            desc = f"{j.get('description', '')} {j.get('qualifications', '')} {j.get('responsibilities', '')}"
            decision = self.filter.evaluate(title, loc, desc)
            if decision.is_eligible:
                apply_url = j.get("apply_url") or j.get("canonical_url") or f"https://{host}/careers-home/jobs/{j.get('slug', '')}"
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": str(j.get("req_id") or j.get("slug") or ""),
                    "title": title.strip(),
                    "location": loc.strip(),
                    "posted_on": format_posted_date(j.get("posted_date") or j.get("create_date")),
                    "canonical_url": apply_url,
                    "reason": decision.reason,
                })

        return report

    # =========================================================================
    # 10. GOOGLE CAREERS (Paginated India Search + Individual Job Page JD)
    # =========================================================================
    def scan_google(self, company: str) -> CompanyScanReport:
        report = CompanyScanReport(company=company, scanner_type="google_careers", status="SCANNED_OK")
        seen_urls = set()
        candidates = []
        any_success = False

        queries = [
            "Software Engineer University Graduate",
            "Software Engineering Intern",
            "Software Engineer Early Career",
            "Machine Learning Intern",
        ]
        for q in queries:
            for page in range(1, 5):
                url = "https://www.google.com/about/careers/applications/jobs/results/"
                resp = self._request("GET", url, params={"location": "India", "q": q, "page": page})
                if resp is None or resp.status_code != 200:
                    break
                any_success = True
                soup = BeautifulSoup(resp.text, "html.parser")
                found_on_page = 0
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "jobs/results/" in href and re.search(r"jobs/results/\d+-", href):
                        full_url = urljoin("https://www.google.com/about/careers/applications/", href).split("?")[0]
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            found_on_page += 1
                            # Extract title from slug or link text
                            slug_part = full_url.rstrip("/").split("/")[-1]
                            title_guess = re.sub(r"^\d+-", "", slug_part).replace("-", " ").title()
                            candidates.append((full_url, title_guess))
                if found_on_page < 15:
                    break
                time.sleep(0.3)

        if not any_success:
            report.status = "FAILED"
            report.error = "Google Careers unreachable"
            return report

        report.total_retrieved = len(candidates)

        for job_url, title_guess in candidates:
            if not self._preliminary_check(title_guess, "India"):
                continue

            report.candidate_jds_checked += 1
            d_resp = self._request("GET", job_url)
            if d_resp is None or d_resp.status_code != 200:
                continue

            soup = BeautifulSoup(d_resp.text, "html.parser")
            h1 = soup.find("h1")
            title = h1.get_text(" ", strip=True) if h1 else title_guess
            # Google embeds title in h2.p1N2lc on job pages sometimes
            if title.lower() in ("google careers", "careers", ""):
                h2 = soup.find("h2")
                if h2:
                    title = h2.get_text(" ", strip=True)
            body_text = soup.get_text(" ", strip=True)

            # Confirm India appears on the job page itself
            decision = self.filter.evaluate(title, "India" if "india" in body_text.lower() else "", body_text)
            if decision.is_eligible:
                jid = re.search(r"jobs/results/(\d+)-", job_url)
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": jid.group(1) if jid else job_url,
                    "title": title,
                    "location": "India",
                    "posted_on": "Not disclosed",
                    "canonical_url": job_url,
                    "reason": decision.reason,
                })
            time.sleep(0.25)

        return report

    # =========================================================================
    # 11. TALENTBREW PORTAL ADAPTER (Barclays, Intuit, Synopsys, Palo Alto)
    # =========================================================================
    def scan_talentbrew(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        base_url = cfg["base_url"].rstrip("/")
        paths = cfg.get("search_paths", ["/search-jobs/India"])
        report = CompanyScanReport(company=company, scanner_type="talentbrew", status="SCANNED_OK")

        seen_urls = set()
        candidates = []
        any_success = False
        last_err = ""

        for p in paths:
            url = f"{base_url}{p}"
            resp = self._request("GET", url)
            if resp is None or resp.status_code != 200:
                last_err = f"HTTP {resp.status_code if resp else 'timeout'}"
                continue
            any_success = True
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/job/" not in href:
                    continue
                full_url = urljoin(base_url, href).split("?")[0]
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                h2 = a.find(["h2", "h3"])
                title = h2.get_text(" ", strip=True) if h2 else a.get_text(" ", strip=True)
                loc_el = a.find("span", class_=re.compile("location", re.I))
                loc = loc_el.get_text(" ", strip=True) if loc_el else ""
                # Also infer location from URL path (/job/pune/..., /job/bengaluru/...)
                loc_combined = f"{loc} {href.replace('-', ' ').replace('/', ' ')}"
                candidates.append((full_url, title, loc_combined))
            time.sleep(0.25)

        if not any_success:
            report.status = "FAILED"
            report.error = f"TalentBrew portal unreachable ({last_err})"
            return report

        report.total_retrieved = len(candidates)

        for job_url, title, loc_hint in candidates:
            if not self._preliminary_check(title, loc_hint):
                continue
            loc_ok, _ = self.filter.check_location(loc_hint, title)
            if not loc_ok:
                continue

            # Fetch individual job page to read ACTUAL JD & posting date!
            report.candidate_jds_checked += 1
            d_resp = self._request("GET", job_url)
            if d_resp is None or d_resp.status_code != 200:
                continue

            soup = BeautifulSoup(d_resp.text, "html.parser")
            h1 = soup.find("h1")
            if h1 and len(h1.get_text(strip=True)) > 3:
                title = h1.get_text(" ", strip=True)

            # Extract posting date from meta or JSON-LD if present
            posted_raw = None
            m_date = re.search(r'"datePosted"\s*:\s*"([^"]+)"', d_resp.text)
            if m_date:
                posted_raw = m_date.group(1)

            main_el = soup.find("section", class_=re.compile("job-description", re.I)) or soup.find("main") or soup
            desc_text = main_el.get_text(" ", strip=True)

            decision = self.filter.evaluate(title, loc_hint, desc_text)
            if decision.is_eligible:
                jid = job_url.rstrip("/").split("/")[-1]
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": jid,
                    "title": title,
                    "location": "India",
                    "posted_on": format_posted_date(posted_raw),
                    "canonical_url": job_url,
                    "reason": decision.reason,
                })
            time.sleep(0.2)

        return report

    # =========================================================================
    # 12. DEDICATED ATTEMPTS FOR APPLE, UBER, GOLDMAN SACHS & GENERIC PORTALS
    # =========================================================================
    def scan_apple(self, company: str) -> CompanyScanReport:
        report = CompanyScanReport(company=company, scanner_type="apple_api", status="SCANNED_OK")
        url = "https://jobs.apple.com/api/role/search"
        seen = set()
        raw = []
        any_ok = False
        last_err = ""

        for kw in ["software engineer", "intern", "machine learning"]:
            for page in range(1, 5):
                payload = {
                    "query": kw,
                    "filters": {"locations": ["postLocation-IND"]},
                    "page": page,
                    "locale": "en-us",
                    "sort": "newest",
                }
                resp = self._request(
                    "POST", url, json=payload,
                    headers={**DEFAULT_HEADERS, "Content-Type": "application/json", "Referer": "https://jobs.apple.com/en-in/search"}
                )
                if resp is None or resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code if resp else 'timeout'}"
                    break
                any_ok = True
                results = resp.json().get("searchResults", [])
                if not results:
                    break
                for r in results:
                    pid = str(r.get("positionId", ""))
                    if pid and pid not in seen:
                        seen.add(pid)
                        raw.append(r)
                if len(results) < 20:
                    break

        if not any_ok:
            report.status = "FAILED"
            report.error = f"Apple API blocked/unreachable ({last_err})"
            return report

        report.total_retrieved = len(raw)
        for r in raw:
            title = r.get("postingTitle", "")
            locs = " ".join(l.get("name", "") for l in (r.get("locations") or []))
            if not self._preliminary_check(title, locs):
                continue
            report.candidate_jds_checked += 1
            desc = f"{r.get('jobSummary', '')}"
            pid = str(r.get("positionId", ""))
            # Fetch detail endpoint for full qualifications
            d_resp = self._request("GET", f"https://jobs.apple.com/api/role/detail/{pid}?locale=en-us")
            if d_resp is not None and d_resp.status_code == 200:
                det = d_resp.json()
                desc = f"{det.get('jobSummary', '')} {det.get('description', '')} {det.get('keyQualifications', '')} {det.get('education', '')}"

            decision = self.filter.evaluate(title, locs, desc)
            if decision.is_eligible:
                apply_url = f"https://jobs.apple.com/en-in/details/{pid}/{r.get('transformedPostingTitle', '')}"
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": pid,
                    "title": title.strip(),
                    "location": locs.strip() or "India",
                    "posted_on": format_posted_date(r.get("postingDate")),
                    "canonical_url": apply_url,
                    "reason": decision.reason,
                })
        return report

    def scan_uber(self, company: str) -> CompanyScanReport:
        report = CompanyScanReport(company=company, scanner_type="uber_api", status="SCANNED_OK")
        url = "https://www.uber.com/api/loadSearchJobsResults?localeCode=en"
        resp = self._request(
            "POST", url,
            json={"limit": 50, "page": 0, "params": {"location": [{"country": "IND"}], "query": "Software"}},
            headers={**DEFAULT_HEADERS, "Content-Type": "application/json", "x-csrf-token": "x", "Origin": "https://www.uber.com", "Referer": "https://www.uber.com/in/en/careers/list/"}
        )
        if resp is None or resp.status_code != 200:
            report.status = "FAILED"
            report.error = f"Uber API blocked/unreachable ({resp.status_code if resp else 'timeout'})"
            return report

        results = resp.json().get("data", {}).get("results", [])
        report.total_retrieved = len(results)
        for r in results:
            title = r.get("title", "")
            loc_obj = r.get("location") or {}
            loc = f"{loc_obj.get('city', '')}, {loc_obj.get('countryName', '')}"
            if not self._preliminary_check(title, loc):
                continue
            report.candidate_jds_checked += 1
            desc = r.get("description", "")
            decision = self.filter.evaluate(title, loc, desc)
            if decision.is_eligible:
                jid = str(r.get("id", ""))
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": jid,
                    "title": title.strip(),
                    "location": loc.strip(),
                    "posted_on": format_posted_date(r.get("creationDate")),
                    "canonical_url": f"https://www.uber.com/global/en/careers/list/{jid}/",
                    "reason": decision.reason,
                })
        return report

    def scan_goldman(self, company: str) -> CompanyScanReport:
        report = CompanyScanReport(company=company, scanner_type="goldman_api", status="SCANNED_OK")
        gql = {
            "operationName": "GetRoles",
            "variables": {
                "searchQueryInput": {
                    "page": {"pageSize": 50, "pageNumber": 0},
                    "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                    "filters": [{"filterCategoryType": "LOCATION", "filters": [{"filter": "India"}]}],
                    "experiences": ["NEW_ANALYST", "SUMMER_ANALYST", "INTERN"],
                    "searchTerm": "Engineer",
                }
            },
            "query": "query GetRoles($searchQueryInput: RoleSearchQueryInput!) { roleSearch(searchQueryInput: $searchQueryInput) { totalCount items { roleId jobTitle corporateTitle locations { city country } } } }"
        }
        resp = self._request("POST", "https://api-higher.gs.com/gateway/api/v1/graphql", json=gql, headers={**DEFAULT_HEADERS, "Content-Type": "application/json"})
        if resp is None or resp.status_code != 200:
            report.status = "FAILED"
            report.error = f"Goldman Sachs API blocked/unreachable ({resp.status_code if resp else 'timeout'})"
            return report

        items = (resp.json().get("data") or {}).get("roleSearch", {}).get("items", [])
        report.total_retrieved = len(items)
        for it in items:
            title = it.get("jobTitle", "")
            locs = ", ".join(f"{l.get('city', '')}, {l.get('country', '')}" for l in (it.get("locations") or []))
            if not self._preliminary_check(title, locs):
                continue
            rid = str(it.get("roleId", ""))
            apply_url = f"https://higher.gs.com/roles/{rid}"
            report.candidate_jds_checked += 1
            d_resp = self._request("GET", apply_url)
            desc = BeautifulSoup(d_resp.text, "html.parser").get_text(" ", strip=True) if (d_resp and d_resp.status_code == 200) else ""
            decision = self.filter.evaluate(title, locs, desc)
            if decision.is_eligible:
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": rid,
                    "title": title.strip(),
                    "location": locs or "India",
                    "posted_on": "Not disclosed",
                    "canonical_url": apply_url,
                    "reason": decision.reason,
                })
        return report

    def scan_portal_html(self, company: str, cfg: Dict[str, Any]) -> CompanyScanReport:
        """
        Attempts to extract genuine individual job links from HTML career portals
        (SAP Labs, Nutanix, Zerodha, etc.) and inspects individual job pages.
        If the portal is JS-gated / blocked / yields 0 job links, marks FAILED accurately!
        """
        urls = cfg.get("urls", [])
        report = CompanyScanReport(company=company, scanner_type="portal_html", status="SCANNED_OK")

        seen_links = set()
        candidates = []
        any_http_ok = False
        last_err = ""

        for u in urls:
            resp = self._request("GET", u, allow_redirects=True)
            if resp is None or resp.status_code != 200:
                last_err = f"HTTP {resp.status_code if resp else 'timeout'}"
                continue
            any_http_ok = True
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if any(cue in href.lower() for cue in ["/job/", "/jobs/", "/position/", "/requisition/", "/opening/", "/careers/details/"]):
                    full_url = urljoin(resp.url, href).split("#")[0]
                    # Skip generic search/index pages
                    if re.search(r"/(?:jobs|careers|search|search-jobs|open-positions)/?$", full_url.split("?")[0].lower()):
                        continue
                    if full_url not in seen_links:
                        seen_links.add(full_url)
                        title = a.get_text(" ", strip=True)
                        if 4 < len(title) < 130:
                            candidates.append((full_url, title))

        if not any_http_ok:
            report.status = "FAILED"
            report.error = f"Portal unreachable ({last_err})"
            return report

        if len(candidates) == 0:
            report.status = "FAILED"
            report.error = "JS-rendered/SPA portal or bot-protected (0 static job links accessible via HTTP)"
            return report

        report.total_retrieved = len(candidates)

        for job_url, title in candidates[:60]:
            if not self._preliminary_check(title, "India"):
                continue
            report.candidate_jds_checked += 1
            d_resp = self._request("GET", job_url, allow_redirects=True)
            if d_resp is None or d_resp.status_code != 200:
                continue
            soup = BeautifulSoup(d_resp.text, "html.parser")
            desc_text = soup.get_text(" ", strip=True)
            posted_raw = None
            m_date = re.search(r'"datePosted"\s*:\s*"([^"]+)"', d_resp.text)
            if m_date:
                posted_raw = m_date.group(1)

            loc_hint = "India" if "india" in desc_text.lower() else ""
            decision = self.filter.evaluate(title, loc_hint, desc_text)
            if decision.is_eligible:
                report.fresher_matches.append({
                    "company_name": company,
                    "ats_job_id": job_url.rstrip("/").split("/")[-1],
                    "title": title,
                    "location": "India",
                    "posted_on": format_posted_date(posted_raw),
                    "canonical_url": job_url,
                    "reason": decision.reason,
                })
            time.sleep(0.2)

        return report

    # =========================================================================
    # DISPATCHER FOR ANY COMPANY IN companies.json
    # =========================================================================
    def scan_company(self, company_entry: Dict[str, Any]) -> CompanyScanReport:
        name = company_entry["name"]
        cfg = company_entry.get("scanner", {"type": "portal_html", "urls": [company_entry.get("careers_url", "")]})
        stype = cfg.get("type", "portal_html")

        try:
            if stype == "workday":
                return self.scan_workday(name, cfg)
            elif stype == "oracle_hcm":
                return self.scan_oracle_hcm(name, cfg)
            elif stype == "greenhouse":
                return self.scan_greenhouse(name, cfg)
            elif stype == "lever":
                return self.scan_lever(name, cfg)
            elif stype == "smartrecruiters":
                return self.scan_smartrecruiters(name, cfg)
            elif stype == "eightfold_pcsx":
                return self.scan_eightfold_pcsx(name, cfg)
            elif stype == "amazon_api":
                return self.scan_amazon(name)
            elif stype == "atlassian_api":
                return self.scan_atlassian(name)
            elif stype == "jibe_api":
                return self.scan_jibe(name, cfg)
            elif stype == "google_careers":
                return self.scan_google(name)
            elif stype == "talentbrew":
                return self.scan_talentbrew(name, cfg)
            elif stype == "apple_api":
                return self.scan_apple(name)
            elif stype == "uber_api":
                return self.scan_uber(name)
            elif stype == "goldman_api":
                return self.scan_goldman(name)
            else:
                return self.scan_portal_html(name, cfg)
        except Exception as e:
            return CompanyScanReport(
                company=name,
                scanner_type=stype,
                status="FAILED",
                error=f"Unhandled scanner exception: {e}"
            )
