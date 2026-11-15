"""
Hunter 2.0 Authenticity & Application Verification
Verifies that job opportunities actually exist, their official application URLs are accessible,
and they are actively accepting applications (not expired, closed, or 404).
"""

import re
import requests
from typing import Dict, Any, Tuple, Optional

TIMEOUT = 12

# Common indicators of closed or expired listings
CLOSED_PAGE_INDICATORS = [
    r"this (?:job|position|opening|posting) is (?:no longer (?:available|active|accepting applications)|closed|filled|expired)",
    r"no longer accepting (?:applications|submissions|candidates)",
    r"job (?:has expired|has been closed|not found)",
    r"the page you are looking for (?:cannot be found|has been removed|does not exist)",
    r"404 - page not found",
    r"position has been filled",
    r"this requisition is no longer active",
    r"applications for this role are now closed"
]


class AuthenticityVerifier:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

    def verify_application_url(self, url: str) -> Tuple[bool, str, Optional[str]]:
        """
        Verifies that an application URL is active and accessible.
        Returns: (is_valid, reason, canonical_url)
        """
        if not url or not url.startswith("http"):
            return False, "Invalid or empty application URL", None

        # Check for raw internal API endpoints that candidates cannot apply through
        bad_api_domains = ["boards-api.greenhouse.io", "api.smartrecruiters.com/v1"]
        if any(d in url for d in bad_api_domains):
            return False, "URL is a raw JSON API endpoint, not an accessible application page", None

        try:
            # First try a lightweight HEAD request
            response = self.session.head(url, timeout=TIMEOUT, allow_redirects=True)
            if response.status_code in [404, 410]:
                return False, f"Job listing returned HTTP {response.status_code} (Not Found / Gone)", None

            # If HEAD is disallowed (e.g. 405 Method Not Allowed) or inconclusive, perform GET
            if response.status_code != 200:
                response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)

            if response.status_code != 200:
                return False, f"Application page returned HTTP {response.status_code}", None

            canonical_url = response.url

            # Inspect page content for closure / expiration notices
            text_snippet = response.text[:15000].lower()
            for pattern in CLOSED_PAGE_INDICATORS:
                if re.search(pattern, text_snippet):
                    return False, f"Application page indicates listing is closed ('{pattern}')", canonical_url

            return True, "Application page is active and verified", canonical_url

        except requests.exceptions.Timeout:
            return False, "Application URL timed out while verifying", None
        except requests.exceptions.RequestException as e:
            return False, f"Application URL network error: {str(e)}", None

    @staticmethod
    def is_known_ats_platform(url: str) -> bool:
        """
        Checks if the URL is on a recognized high-trust ATS platform.
        """
        known_platforms = [
            "greenhouse.io", "lever.co", "smartrecruiters.com", "myworkdayjobs.com",
            "ashbyhq.com", "icims.com", "taleo.net", "jobvite.com", "workable.com"
        ]
        return any(platform in url.lower() for platform in known_platforms)
