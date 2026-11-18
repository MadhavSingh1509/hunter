"""
Hunter — Simple Email Alert Bridge
Delegates to notifications/email_service.py for the minimal 4-field digest.
"""

from typing import List, Tuple, Any
from notifications.email_service import HunterEmailService


def build_email_digest(jobs: List[Any], potential_matches: Any = None) -> Tuple[str, str, str]:
    job_dicts = [j if isinstance(j, dict) else j.__dict__ for j in (jobs or [])]
    return HunterEmailService.build_simple_digest(job_dicts)


def send_email_digest(jobs: List[Any], potential_matches: Any = None) -> bool:
    job_dicts = [j if isinstance(j, dict) else j.__dict__ for j in (jobs or [])]
    return HunterEmailService().send_simple_digest(job_dicts)
