"""
Configuration loader for Hunter 2.0.
Loads candidate profile, target categories, scoring weights, and environment overrides.
"""

import json
import os
from typing import Dict, Any, List

DEFAULT_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "candidate_profile.json")


def load_candidate_profile(path: str = DEFAULT_PROFILE_PATH) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    else:
        profile = {
            "candidate": {
                "name": "Madhav Singh",
                "degree": "B.Tech",
                "branch": "Electrical Engineering",
                "branch_aliases": ["EE", "Electrical", "Electrical Engineering", "EEE"],
                "candidate_type": "Fresher",
                "graduation_year": 2026,
                "eligible_graduation_years": [2025, 2026],
                "experience_years_max": 0,
                "has_professional_software_experience": false,
                "location_country": "India",
                "technical_skills": [
                    "C++", "Java", "Python", "JavaScript", "HTML", "CSS", "React.js",
                    "Node.js", "Express.js", "MongoDB", "SQL", "Data Structures and Algorithms",
                    "REST APIs", "Git", "GitHub"
                ],
            },
            "target_categories": {},
            "scoring_weights": {},
            "thresholds": {"verified_match_min_score": 75, "potential_match_min_score": 50}
        }

    # Environment variable overrides
    if "HUNTER_GRADUATION_YEAR" in os.environ:
        try:
            val = int(os.environ["HUNTER_GRADUATION_YEAR"])
            profile["candidate"]["graduation_year"] = val
            if val not in profile["candidate"].get("eligible_graduation_years", []):
                profile["candidate"]["eligible_graduation_years"] = [val - 1, val]
        except ValueError:
            pass

    if "HUNTER_LOCATION" in os.environ:
        profile["candidate"]["location_country"] = os.environ["HUNTER_LOCATION"]

    return profile
