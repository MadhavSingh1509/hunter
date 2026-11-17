"""
Hunter 4.0 - Email Alert System (Bridge & Compatibility Layer)
Delegates to notifications/email_service.py for the 4-section digest.
"""

import os
from typing import List, Tuple, Optional, Any
from notifications.email_service import HunterEmailService

def build_email_digest(
    verified_matches: List[Any],
    potential_matches: Optional[List[Any]] = None
) -> Tuple[str, str, str]:
    """
    Constructs the Subject, Plain-text body, and HTML body for the digest.
    Returns: (subject, plain_text, html_body)
    """
    potential_matches = potential_matches or []
    count = len(verified_matches)
    pot_count = len(potential_matches)

    # Convert object attributes to dicts if needed
    ver_dicts = [m if isinstance(m, dict) else m.__dict__ for m in verified_matches]
    pot_dicts = [m if isinstance(m, dict) else m.__dict__ for m in potential_matches]

    service = HunterEmailService()
    scan_summary = {
        "companies_scanned": 167,
        "jobs_retrieved": count + pot_count
    }
    
    html_body = service.generate_html_digest(ver_dicts, pot_dicts, [], [], scan_summary)
    subject = f"🎯 Hunter 4.0: {count} Verified | {pot_count} Potential Fresher SDE/AI Jobs"
    plain_text = f"Hunter 4.0 Job Alert\nVerified: {count}\nPotential: {pot_count}\nPlease open the HTML version for direct apply links."

    return subject, plain_text, html_body

def send_email_digest(
    verified_matches: List[Any],
    potential_matches: Optional[List[Any]] = None
) -> bool:
    """Sends email digest using HunterEmailService."""
    ver_dicts = [m if isinstance(m, dict) else m.__dict__ for m in (verified_matches or [])]
    pot_dicts = [m if isinstance(m, dict) else m.__dict__ for m in (potential_matches or [])]
    
    service = HunterEmailService()
    scan_summary = {
        "companies_scanned": 167,
        "jobs_retrieved": len(ver_dicts) + len(pot_dicts)
    }
    return service.send_digest(ver_dicts, pot_dicts, [], [], scan_summary)
