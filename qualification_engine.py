"""
Hunter 2.0 Qualification Engine
Multi-stage deterministic job qualification and scoring pipeline.
Evaluates opportunities against a centralized candidate profile with strict rejection gates.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple

# Rejection categories
REJECT_EXPERIENCE = "Mandatory experience requirement exceeds fresher profile (2+ years / mid-senior)"
REJECT_DEGREE_BRANCH = "Degree or branch restriction excludes Electrical Engineering (e.g., CSE/IT only or Master's required)"
REJECT_GRAD_YEAR = "Graduation batch restriction in conflict with candidate graduation year"
REJECT_LOCATION = "Job location is outside India or not open to India residents"
REJECT_SENIORITY_ROLE = "Senior, lead, managerial, or non-software engineering role"
REJECT_CLOSED = "Job listing is closed, expired, or application page is inaccessible"
REJECT_AUTH = "Requires specific foreign work authorization or active security clearance"


@dataclass
class JobPosting:
    company: str
    title: str
    url: str
    location: str = ""
    description: str = ""
    job_id: str = ""
    posted_date: str = ""
    job_type: str = "Full-time"  # Full-time, Internship, Contract
    is_active: bool = True
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualificationResult:
    job: JobPosting
    verdict: str  # "VERIFIED MATCH", "POTENTIAL MATCH", "REJECTED"
    score: int  # 0 to 100
    rejection_reasons: List[str] = field(default_factory=list)
    uncertain_flags: List[str] = field(default_factory=list)
    match_highlights: List[str] = field(default_factory=list)
    tier: str = "Tier 1"
    details: Dict[str, Any] = field(default_factory=dict)

    def is_actionable(self) -> bool:
        return self.verdict == "VERIFIED MATCH"


class QualificationEngine:
    """
    Intelligent qualification engine implementing the 10-stage evaluation pipeline.
    """

    # Indian locations & hubs
    INDIA_LOCATIONS = {
        "india", "bangalore", "bengaluru", "hyderabad", "pune", "gurgaon", "gurugram",
        "noida", "delhi", "delhi ncr", "mumbai", "chennai", "kolkata", "ahmedabad",
        "kochi", "cochin", "jaipur", "indore", "chandigarh", "coimbatore", "vizag",
        "visakhapatnam", "trivandrum", "thiruvananthapuram"
    }

    NON_INDIA_LOCATIONS = {
        "usa", "united states", "us", "san francisco", "seattle", "new york", "austin",
        "boston", "chicago", "los angeles", "london", "united kingdom", "uk", "singapore",
        "germany", "berlin", "canada", "toronto", "vancouver", "australia", "sydney",
        "melbourne", "ireland", "dublin", "amsterdam", "netherlands", "tokyo", "japan",
        "poland", "warsaw", "dubai", "uae", "israel", "tel aviv", "china"
    }

    # Seniority titles that must be rejected
    SENIOR_KEYWORDS = [
        r"\bsenior\b", r"\bsr\.?\b", r"\bstaff\b", r"\bprincipal\b", r"\blead\b",
        r"\bmanager\b", r"\bdirector\b", r"\barchitect\b", r"\bvp\b", r"\bhead of\b",
        r"\bdistinguished\b", r"\bchief\b", r"\bexecutive\b", r"\bpartner\b"
    ]

    # Non-software / excluded departments
    NON_SOFTWARE_KEYWORDS = [
        r"\bhuman resources\b", r"\bhr\b", r"\brecruiter\b", r"\btalent acquisition\b",
        r"\bsales\b", r"\bbusiness development\b", r"\bcustomer support\b",
        r"\btechnical support\b", r"\btech support\b", r"\bmarketing\b", r"\bfinance\b",
        r"\baccountant\b", r"\blegal\b", r"\boperations executive\b", r"\bproduct manager\b",
        r"\bprogram manager\b", r"\bproject manager\b", r"\bdata entry\b"
    ]

    # Core electrical roles that are NOT software
    CORE_ELECTRICAL_KEYWORDS = [
        r"\bsubstation\b", r"\btransformer\b", r"\bswitchgear\b", r"\bpower systems\b",
        r"\bpower plant\b", r"\blineman\b", r"\belectrician\b", r"\bwiring\b",
        r"\bhigh voltage\b", r"\bsite engineer \(electrical\)\b", r"\bmaintenance technician\b"
    ]

    def __init__(self, profile: Dict[str, Any]):
        self.profile = profile
        self.candidate = profile.get("candidate", {})
        self.target_categories = profile.get("target_categories", {})
        self.scoring_weights = profile.get("scoring_weights", {
            "role_relevance": 25,
            "experience_eligibility": 20,
            "educational_eligibility": 20,
            "graduation_year_eligibility": 15,
            "technical_skill_alignment": 10,
            "location_and_work_arrangement": 10
        })
        self.thresholds = profile.get("thresholds", {
            "verified_match_min_score": 75,
            "potential_match_min_score": 50
        })

    def evaluate(self, job: JobPosting) -> QualificationResult:
        """
        Executes the full 10-stage evaluation pipeline on a JobPosting.
        """
        rejection_reasons: List[str] = []
        uncertain_flags: List[str] = []
        match_highlights: List[str] = []
        scores: Dict[str, int] = {}
        details: Dict[str, Any] = {}

        # ---------------- STAGE 7: Application Active Verification ----------------
        if not job.is_active:
            rejection_reasons.append(REJECT_CLOSED)
            return QualificationResult(
                job=job, verdict="REJECTED", score=0,
                rejection_reasons=rejection_reasons, details={"status": "inactive"}
            )

        # ---------------- STAGE 2: Title Classification & Seniority Gate ----------------
        title_verdict, tier, title_score, title_notes = self._classify_title(job.title, job.description)
        scores["role_relevance"] = title_score
        details["role_tier"] = tier
        if title_verdict == "REJECT":
            rejection_reasons.append(title_notes)
        elif title_verdict == "UNCERTAIN":
            uncertain_flags.append(title_notes)
        else:
            match_highlights.append(title_notes)

        # ---------------- STAGE 5: Location Analysis ----------------
        loc_verdict, loc_score, loc_notes = self._evaluate_location(job.location, job.description)
        scores["location_and_work_arrangement"] = loc_score
        if loc_verdict == "REJECT":
            rejection_reasons.append(loc_notes)
        elif loc_verdict == "UNCERTAIN":
            uncertain_flags.append(loc_notes)
        else:
            match_highlights.append(loc_notes)

        # ---------------- STAGE 3: Strict Experience Filtering ----------------
        exp_verdict, exp_score, exp_notes, exp_data = self._evaluate_experience(job.title, job.description, job.job_type)
        scores["experience_eligibility"] = exp_score
        details["experience"] = exp_data
        if exp_verdict == "REJECT":
            rejection_reasons.append(exp_notes)
        elif exp_verdict == "UNCERTAIN":
            uncertain_flags.append(exp_notes)
        else:
            match_highlights.append(exp_notes)

        # ---------------- STAGE 4: Educational Eligibility Filter (EE Degree) ----------------
        edu_verdict, edu_score, edu_notes, edu_data = self._evaluate_education(job.title, job.description)
        scores["educational_eligibility"] = edu_score
        details["education"] = edu_data
        if edu_verdict == "REJECT":
            rejection_reasons.append(edu_notes)
        elif edu_verdict == "UNCERTAIN":
            uncertain_flags.append(edu_notes)
        else:
            match_highlights.append(edu_notes)

        # ---------------- STAGE 7: Graduation Year & Internship Filter ----------------
        grad_verdict, grad_score, grad_notes, grad_data = self._evaluate_grad_year_and_internship(
            job.title, job.description, job.job_type
        )
        scores["graduation_year_eligibility"] = grad_score
        details["grad_year"] = grad_data
        if grad_verdict == "REJECT":
            rejection_reasons.append(grad_notes)
        elif grad_verdict == "UNCERTAIN":
            uncertain_flags.append(grad_notes)
        else:
            match_highlights.append(grad_notes)

        # ---------------- STAGE 6: Skill Alignment & Additional Restrictions ----------------
        skill_score, matched_skills, skill_notes = self._evaluate_skills(job.title, job.description)
        scores["technical_skill_alignment"] = skill_score
        details["matched_skills"] = matched_skills
        if skill_notes:
            match_highlights.append(skill_notes)

        # Check work authorization & clearance restrictions
        auth_verdict, auth_notes = self._evaluate_authorization(job.description)
        if auth_verdict == "REJECT":
            rejection_reasons.append(auth_notes)

        # ---------------- STAGE 8: Candidate Matching & Scoring ----------------
        total_score = sum(scores.values())

        # MANDATORY REJECTION GATES OVERRIDE
        if rejection_reasons:
            verdict = "REJECTED"
        elif uncertain_flags or total_score < self.thresholds.get("verified_match_min_score", 75):
            if total_score >= self.thresholds.get("potential_match_min_score", 50):
                verdict = "POTENTIAL MATCH"
            else:
                verdict = "REJECTED"
                rejection_reasons.append(f"Match score ({total_score}/100) below threshold")
        else:
            verdict = "VERIFIED MATCH"

        details["scores"] = scores
        return QualificationResult(
            job=job,
            verdict=verdict,
            score=min(100, max(0, total_score)),
            rejection_reasons=rejection_reasons,
            uncertain_flags=uncertain_flags,
            match_highlights=match_highlights,
            tier=tier,
            details=details
        )

    def _classify_title(self, title: str, description: str) -> Tuple[str, str, int, str]:
        t = title.lower()
        d = description.lower()

        # Check seniority keywords in title
        for pattern in self.SENIOR_KEYWORDS:
            if re.search(pattern, t):
                return "REJECT", "Excluded", 0, f"{REJECT_SENIORITY_ROLE} (matched keyword '{pattern}')"

        # Check numeric seniority like SDE-2, SDE-3, SDE II, Level 4
        if re.search(r"\b(?:sde|swe|software (?:development )?engineer|engineer)[\s\-]*([2-5]|ii|iii|iv|v)\b", t):
            return "REJECT", "Excluded", 0, f"{REJECT_SENIORITY_ROLE} (level >= 2 in title)"

        # Check non-software / excluded departments
        for pattern in self.NON_SOFTWARE_KEYWORDS:
            if re.search(pattern, t):
                return "REJECT", "Excluded", 0, f"{REJECT_SENIORITY_ROLE} (non-development domain '{pattern}')"

        # Check core electrical engineering roles
        for pattern in self.CORE_ELECTRICAL_KEYWORDS:
            if re.search(pattern, t):
                return "REJECT", "Excluded", 0, f"{REJECT_SENIORITY_ROLE} (core electrical role '{pattern}')"

        # Check Graduate Engineer Trainee (GET)
        if "graduate engineer trainee" in t or re.search(r"\bget\b", t):
            software_indicators = ["software", "programming", "python", "java", "developer", "it ", "coding", "web"]
            if any(k in t or k in d for k in software_indicators):
                return "ACCEPT", "Tier 2", 20, "Graduate Engineer Trainee (Software/IT Track)"
            else:
                return "REJECT", "Excluded", 0, f"{REJECT_SENIORITY_ROLE} (GET role without software/IT indication)"

        # Check Tier 1 Primary Targets
        tier_1 = [
            r"\bsoftware development engineer\b", r"\bsde\b", r"\bsoftware engineer\b",
            r"\bassociate software engineer\b", r"\bjunior software developer\b",
            r"\bjunior software engineer\b", r"\bbackend developer\b", r"\bbackend engineer\b",
            r"\bfull stack developer\b", r"\bfull stack engineer\b", r"\bfullstack developer\b",
            r"\bfullstack engineer\b", r"\bfrontend developer\b", r"\bfrontend engineer\b",
            r"\bgraduate software engineer\b", r"\bsoftware engineer i\b",
            r"\bentry-level developer\b", r"\bentry level software engineer\b"
        ]
        for role_pattern in tier_1:
            if re.search(role_pattern, t):
                return "ACCEPT", "Tier 1", 25, f"Tier 1 Primary Role Match: {title}"

        # Check Tier 2 Secondary Targets
        tier_2 = [
            r"\bapplication developer\b", r"\bpython developer\b", r"\bjava developer\b",
            r"\bc\+\+ developer\b", r"\bqa automation engineer\b", r"\bqa engineer\b",
            r"\bsoftware (?:development |engineering )?intern\b", r"\bsde intern\b",
            r"\bbackend (?:engineering )?intern\b", r"\bfull stack (?:engineering )?intern\b",
            r"\bsoftware intern\b"
        ]
        for role_pattern in tier_2:
            if re.search(role_pattern, t):
                return "ACCEPT", "Tier 2", 20, f"Tier 2 Relevant Role Match: {title}"

        # If general engineer with software/tech keywords in title
        if "developer" in t or "programmer" in t or "web developer" in t:
            return "ACCEPT", "Tier 1", 22, f"Target Developer Role Match: {title}"

        return "REJECT", "Excluded", 0, f"Role '{title}' does not match target software developer categories"

    def _evaluate_location(self, location: str, description: str) -> Tuple[str, int, str]:
        combined = f"{location} {description[:300]}".lower()

        # Reject explicit foreign locations if India is not mentioned
        for foreign in self.NON_INDIA_LOCATIONS:
            if re.search(r"\b" + re.escape(foreign) + r"\b", combined):
                loc_lower = location.lower()
                if any(ind in loc_lower for ind in self.INDIA_LOCATIONS):
                    return "ACCEPT", 10, f"Location verified: {location} (India)"
                if not any(ind in combined for ind in self.INDIA_LOCATIONS):
                    return "REJECT", 0, f"{REJECT_LOCATION} (found '{foreign}')"

        for ind in self.INDIA_LOCATIONS:
            if re.search(r"\b" + re.escape(ind) + r"\b", combined):
                return "ACCEPT", 10, f"Location in India verified: {location or ind.title()}"

        if not location.strip():
            return "UNCERTAIN", 5, "Location not disclosed; requires candidate verification"

        return "UNCERTAIN", 5, f"Location '{location}' not recognized as verified India hub"

    def _evaluate_experience(self, title: str, description: str, job_type: str = "Full-time") -> Tuple[str, int, str, Dict[str, Any]]:
        combined = f"{title}\n{description}".lower()

        exp_data = {
            "min_years_required": None,
            "max_years_required": None,
            "is_freshers_explicit": False,
            "is_borderline": False
        }

        # Check for "0-2 years" or "0 to 2 years" FIRST so it is treated as borderline rather than rejected by a 2+ pattern
        if re.search(r"\b0\s*(?:-|to)\s*2\s*years?\b", combined) or "0-2 years" in combined:
            exp_data["min_years_required"] = 0
            exp_data["max_years_required"] = 2
            exp_data["is_borderline"] = True
            return "UNCERTAIN", 14, "Experience requirement is 0-2 years (borderline; requires careful evaluation)", exp_data

        # Check for mandatory high experience patterns (2+ years, 3+ years, min 2 years, etc.)
        mandatory_patterns = [
            r"(?:minimum|min|at least|require[ds]?|must have)\s*([2-9]|\d{2})\+?\s*(?:to\s*\d+\s*)?years?",
            r"\b([2-9]|\d{2})\+?\s*years?\s*(?:(?:of|relevant|professional|industry|software|full-time|prior|hands-on|work)\s+)*experience\b",
            r"\b([2-9])\s*(?:-|to)\s*([4-9]|\d{2})\s*years?\b",
            r"\b2\+\s*years?\s*experience\b"
        ]

        for p in mandatory_patterns:
            m = re.search(p, combined)
            if m:
                matched_span = m.span()
                context = combined[max(0, matched_span[0] - 40):min(len(combined), matched_span[1] + 40)]
                if any(pref in context for pref in ["preferred", "plus", "bonus", "good to have", "advantage"]):
                    continue  # It is preferred, not mandatory
                
                exp_data["min_years_required"] = int(m.group(1))
                return "REJECT", 0, f"{REJECT_EXPERIENCE} (requires {m.group(0)})", exp_data

        # If internship or intern title, experience is inherently entry-level/fresher
        if "intern" in title.lower() or job_type.lower() == "internship":
            exp_data["is_freshers_explicit"] = True
            exp_data["min_years_required"] = 0
            exp_data["max_years_required"] = 0
            return "ACCEPT", 20, "Experience verified: Internship (Students / Recent graduates)", exp_data

        # Check for explicit fresher-friendly phrases
        fresher_cues = [
            "freshers welcome", "freshers can apply", "0 years", "no experience required",
            "entry level", "entry-level", "campus hire", "new grad", "new graduate",
            "college hire", "0 to 1 year", "0-1 year", "0-1 yrs", "0 to 1 yrs",
            "passout", "passing out", "batch"
        ]
        for cue in fresher_cues:
            if cue in combined:
                exp_data["is_freshers_explicit"] = True

        # Check for "0-1 years" or explicit fresher
        if exp_data["is_freshers_explicit"] or re.search(r"\b0\s*(?:-|to)\s*1\s*years?\b", combined):
            exp_data["min_years_required"] = 0
            exp_data["max_years_required"] = 1
            return "ACCEPT", 20, "Experience verified: 0-1 years / Freshers welcome", exp_data

        # Check single year pattern: "1 year", "1+ year"
        if re.search(r"\b1\+?\s*years?\b", combined):
            exp_data["min_years_required"] = 1
            return "ACCEPT", 18, "Experience requirement: ~1 year (entry-level eligible)", exp_data

        # If no experience requirement is mentioned at all
        return "UNCERTAIN", 10, "Experience requirement not disclosed in job description", exp_data

    def _evaluate_education(self, title: str, description: str) -> Tuple[str, int, str, Dict[str, Any]]:
        combined = f"{title}\n{description}".lower()

        edu_data = {
            "degree_matched": None,
            "branch_status": "NOT DISCLOSED",
            "ee_eligible": False
        }

        # Check Master's / Ph.D mandatory requirement
        masters_mandatory = [
            r"(?:must have|requires?|mandatory)\s*(?:a\s*)?(?:master'?s|m\.?tech|ms|ph\.?d)\b",
            r"\bmaster'?s\s+degree\s+required\b",
            r"\bm\.?tech\s+mandatory\b"
        ]
        for pattern in masters_mandatory:
            if re.search(pattern, combined):
                return "REJECT", 0, f"{REJECT_DEGREE_BRANCH} (Requires Master's/Ph.D)", edu_data

        # Check strictly restricted to CSE / IT only
        cse_only_patterns = [
            r"\bonly\s+(?:cse|cs|it|computer science)\b",
            r"\b(?:cse|cs|it|computer science)\s+(?:only|graduates? only)\b",
            r"\bstrictly\s+(?:cse|cs|it|computer science)\b",
            r"\bb\.?tech\s+in\s+computer\s+science\s+only\b",
            r"\bdegree\s+in\s+computer\s+science\s+only\b",
            r"\bopen\s+only\s+to\s+computer\s+science\b"
        ]
        for pattern in cse_only_patterns:
            if re.search(pattern, combined):
                return "REJECT", 0, f"{REJECT_DEGREE_BRANCH} (Strictly restricted to CSE/IT)", edu_data

        # Check if Electrical Engineering is explicitly accepted
        ee_patterns = [
            r"\belectrical\s+engineering\b", r"\belectrical\b", r"\beee\b", r"\bee\b",
            r"\belectrical\s+and\s+electronics\b"
        ]
        for pattern in ee_patterns:
            if re.search(pattern, combined):
                edu_data["degree_matched"] = "B.Tech/B.E."
                edu_data["branch_status"] = "EXPLICIT_EE"
                edu_data["ee_eligible"] = True
                return "ACCEPT", 20, "Educational eligibility verified: Electrical Engineering explicitly accepted", edu_data

        # Check for open branch / all engineering accepted
        open_branch_patterns = [
            r"(?:b\.?tech|b\.?e\.?|bachelor'?s?)[\w\s]{0,15}any\s*(?:engineering\s*)?branch",
            r"any\s*(?:b\.?tech|b\.?e\.?|engineering\s*branch)",
            r"all\s*engineering\s*(?:branches?|disciplines?)",
            r"any\s*(?:engineering\s*)?discipline",
            r"bachelor'?s?\s+degree\s+in\s+engineering\s+or\s+equivalent",
            r"circuit\s+branches?",
            r"(?:b\.?tech|b\.?e\.?)[\w\s]{0,15}any\s*specialization"
        ]
        for pattern in open_branch_patterns:
            if re.search(pattern, combined):
                edu_data["degree_matched"] = "B.Tech/B.E."
                edu_data["branch_status"] = "ALL_BRANCHES"
                edu_data["ee_eligible"] = True
                return "ACCEPT", 20, "Educational eligibility verified: Any engineering discipline / B.Tech accepted", edu_data

        # Check standard degree mention: "B.Tech / B.E. in Computer Science or related field / equivalent"
        if re.search(r"b\.?tech|b\.?e\.?|bachelor'?s?\s+in\s+(?:cs|it|engineering|technology)", combined):
            if "or related" in combined or "or equivalent" in combined or "related technical field" in combined:
                edu_data["degree_matched"] = "B.Tech / Equivalent"
                edu_data["branch_status"] = "RELATED_FIELD"
                edu_data["ee_eligible"] = True
                return "ACCEPT", 18, "Degree eligible: B.Tech in Engineering or related quantitative/technical field", edu_data

        # If degree is not disclosed
        if "degree" not in combined and "b.tech" not in combined and "bachelor" not in combined:
            edu_data["branch_status"] = "NOT DISCLOSED"
            return "UNCERTAIN", 12, "Educational degree and branch requirement NOT DISCLOSED in posting", edu_data

        # If it mentions CS/IT without explicitly excluding or including other branches
        if re.search(r"\b(?:computer science|information technology|cs|it)\b", combined):
            edu_data["branch_status"] = "UNCERTAIN_PREFERENCE"
            return "UNCERTAIN", 10, "CS/IT background preferred; Electrical Engineering eligibility not explicitly stated", edu_data

        return "UNCERTAIN", 10, "Educational branch criteria uncertain", edu_data

    def _evaluate_grad_year_and_internship(
        self, title: str, description: str, job_type: str
    ) -> Tuple[str, int, str, Dict[str, Any]]:
        combined = f"{title}\n{description}".lower()
        candidate_year = self.candidate.get("graduation_year", 2026)
        eligible_years = set(self.candidate.get("eligible_graduation_years", [candidate_year - 1, candidate_year]))

        grad_data = {
            "candidate_year": candidate_year,
            "disclosed_batches": [],
            "status": "NOT DISCLOSED"
        }

        # Check internship specifics:
        if "intern" in title.lower() or job_type.lower() == "internship":
            # Check if restricted to pre-final / 2nd / 3rd year
            has_pre_final = bool(re.search(r"\bpre-final\b", combined))
            has_early_year = bool(re.search(r"\b(?:2nd|second|3rd|third)\s*year\s*(?:students?|only)?\b", combined))
            has_final_year = bool(re.search(r"(?<!pre-)(?<!pre\s)\bfinal\s+year\b", combined))

            if (has_pre_final or has_early_year) and not has_final_year:
                return "REJECT", 0, f"{REJECT_GRAD_YEAR} (Internship restricted to 2nd/3rd year pre-final students)", grad_data

            if has_final_year or "recent graduate" in combined or "graduating class" in combined:
                return "ACCEPT", 15, "Internship verified: Final year / recent graduates explicitly eligible", grad_data

        # Look for explicit batch years like 2024, 2025, 2026, 2027
        year_matches = re.findall(r"\b(202[0-9])\s*(?:passout|batch|graduates?|passing out)?\b", combined)
        detected_years = {int(y) for y in year_matches if 2020 <= int(y) <= 2030}

        filtered_years = set()
        for y in detected_years:
            if re.search(r"\b" + str(y) + r"\s*(?:batch|passout|graduat|passing|class of)\b", combined) or \
               re.search(r"\b(?:batch|passout|graduat|passing|class of)\s*(?:of\s*)?" + str(y) + r"\b", combined):
                filtered_years.add(y)

        grad_data["disclosed_batches"] = sorted(list(filtered_years))

        # If batches are explicitly specified:
        if filtered_years:
            if any(y in eligible_years for y in filtered_years):
                grad_data["status"] = "MATCH"
                return "ACCEPT", 15, f"Graduation batch verified: {sorted(list(filtered_years))} (includes {candidate_year})", grad_data
            else:
                grad_data["status"] = "MISMATCH"
                return "REJECT", 0, f"{REJECT_GRAD_YEAR} (Job restricted to batch {sorted(list(filtered_years))}, candidate is {candidate_year})", grad_data

        # If no batch year is specified
        grad_data["status"] = "NOT DISCLOSED"
        return "ACCEPT", 12, "Graduation batch not restricted / open to all eligible entry-level candidates", grad_data

    def _evaluate_skills(self, title: str, description: str) -> Tuple[int, List[str], str]:
        combined = f"{title}\n{description}".lower()
        matched = []

        skill_patterns = {
            "C++": r"\bc\+\+\b",
            "Java": r"\bjava\b(?!script)",
            "Python": r"\bpython\b",
            "JavaScript": r"\b(?:javascript|js)\b",
            "React.js": r"\breact(?:\.js)?\b",
            "Node.js": r"\bnode(?:\.js)?\b",
            "Express.js": r"\bexpress(?:\.js)?\b",
            "MongoDB": r"\bmongodb\b",
            "SQL": r"\bsql\b",
            "Data Structures and Algorithms": r"\b(?:dsa|data structures|algorithms)\b",
            "REST APIs": r"\brest(?:ful)?\s*api[s]?\b",
            "Git": r"\bgit\b"
        }

        for skill, pattern in skill_patterns.items():
            if re.search(pattern, combined):
                matched.append(skill)

        score = min(10, len(matched) * 2)
        if matched:
            notes = f"Technical skills matched: {', '.join(matched[:5])}"
        else:
            notes = ""

        return score, matched, notes

    def _evaluate_authorization(self, description: str) -> Tuple[str, str]:
        d = description.lower()
        clearance_patterns = [
            r"\bsecurity clearance\s*(?:required|must hold)\b",
            r"\bts/sci\b",
            r"\bsecret clearance\b",
            r"\bus citizenship required\b",
            r"\bgreen card required\b"
        ]
        for p in clearance_patterns:
            if re.search(p, d):
                return "REJECT", f"{REJECT_AUTH} (found '{p}')"
        return "ACCEPT", ""
