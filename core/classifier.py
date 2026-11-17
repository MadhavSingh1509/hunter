"""
Hunter 4.0 - Structured Eligibility Classifier and 100-Point Scoring Engine.
Evaluates 7 dimensions of eligibility with hard rejection gates.
Candidate Profile: B.Tech Electrical Engineering, 2026 Batch, Fresher (0 years full-time software experience).
"""

import re
import os
import json
from typing import Dict, Any, Tuple, List, Optional

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "candidate_profile.json"
)

class EligibilityClassifier:
    def __init__(self, profile_path: str = DEFAULT_CONFIG_PATH):
        self.profile = self.load_profile(profile_path)
        self.candidate = self.profile.get("candidate", {})
        self.target_roles = self.profile.get("target_roles", {})
        self.scoring_weights = self.profile.get("scoring_weights", {
            "role_relevance": 25,
            "degree_eligibility": 20,
            "graduation_eligibility": 15,
            "experience_eligibility": 15,
            "location_eligibility": 10,
            "skills_match": 10,
            "employment_type_preference": 5
        })
        self.thresholds = self.profile.get("thresholds", {
            "verified_match_min_score": 75,
            "potential_match_min_score": 50
        })

    @staticmethod
    def load_profile(path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def classify_role_relevance(self, title: str, description: str = "") -> Tuple[str, float, str]:
        """
        Evaluates role relevance.
        Returns (verdict: 'MATCH' | 'POTENTIAL' | 'REJECTED', score_points, reason).
        """
        text = f"{title} {description}".lower()
        title_lower = title.lower()

        # Hard exclusions: Senior, Management, Non-Tech
        excluded_roles = self.target_roles.get("excluded_roles", [
            "senior", "sr.", "sr ", "staff", "principal", "lead", "manager", "director", "architect",
            "vp", "head of", "distinguished", "sde-2", "sde-3", "sde ii", "sde iii", "sde 2", "sde 3",
            "engineer ii", "engineer iii", "sales", "business development", "customer support", "hr"
        ])
        for exc in excluded_roles:
            pattern = rf"\b{re.escape(exc.strip().lower())}\b"
            if re.search(pattern, title_lower):
                return "REJECTED", 0.0, f"Disqualified title matching excluded role: '{exc}'"

        # Electrical core engineering exclusions (Substation, high voltage, electrician)
        excluded_core = self.target_roles.get("excluded_core_electrical", [
            "substation", "transformer", "switchgear", "electrician", "high voltage", "power plant"
        ])
        for core_kw in excluded_core:
            pattern = rf"\b{re.escape(core_kw.strip().lower())}\b"
            if re.search(pattern, title_lower):
                return "REJECTED", 0.0, f"Disqualified title matching core electrical hardware/field role: '{core_kw}'"

        # Check Target Software Engineering Roles
        software_roles = [r.lower() for r in self.target_roles.get("software_engineering", [])]
        ai_roles = [r.lower() for r in self.target_roles.get("ai_and_machine_learning", [])]

        for s_role in software_roles + ai_roles:
            pattern = rf"\b{re.escape(s_role)}\b"
            if re.search(pattern, title_lower):
                return "MATCH", 25.0, f"Direct title match: '{s_role}'"

        # Pattern matches for common fresher SDE/AI titles
        fresher_patterns = [
            r"\b(?:software|systems?|backend|frontend|full[\s-]?stack|web|api|devops|cloud|sre|platform|mobile|android|ios|ai|ml|data)\s+(?:engineer|developer|trainee|intern)\b",
            r"\b(?:graduate|associate|junior|entry[\s-]?level|fresher|new\s+grad)\s+(?:software|engineer|developer|trainee)\b",
            r"\bsde[\s-]?[1i]\b",
            r"\bsoftware\s+development\s+engineer\b"
        ]
        for pat in fresher_patterns:
            if re.search(pat, title_lower):
                return "MATCH", 25.0, "Matches standard Software/AI engineering title pattern"

        # Check description if title is ambiguous
        if description:
            desc_patterns = [
                r"\b(?:develop|building|implementing|maintain)\s+(?:software|applications|services|apis|microservices)\b",
                r"\b(?:data\s+structures|algorithms|system\s+design|object[\s-]oriented)\b"
            ]
            matches = sum(1 for dp in desc_patterns if re.search(dp, text))
            if matches >= 1:
                return "POTENTIAL", 15.0, "Title is generic but description indicates software engineering responsibilities"

        return "REJECTED", 0.0, "Role is not software engineering or AI/ML"

    def classify_degree_eligibility(self, text: str) -> Tuple[str, float, str]:
        """
        Evaluates Electrical Engineering degree eligibility.
        Candidate has B.Tech in Electrical Engineering (EE).
        Returns (verdict: 'ELIGIBLE' | 'INELIGIBLE' | 'UNKNOWN', score_points, reason).
        """
        text_lower = text.lower()
        if not text_lower:
            return "UNKNOWN", 10.0, "Degree requirements not stated in description (assumed potential)"

        # Hard exclusions: CSE/IT Only
        cs_only_patterns = [
            r"\b(?:only|strictly)\s+(?:for\s+)?(?:computer\s+science|cse|it|information\s+technology)\b",
            r"\bcomputer\s+science\s+(?:only|graduates\s+only)\b",
            r"\b(?:open\s+only\s+to|restricted\s+to)\s+(?:candidates\s+with\s+)?(?:computer\s+science|cse|it)\b",
            r"\bexclusive\s+to\s+cs\b"
        ]
        for cso in cs_only_patterns:
            if re.search(cso, text_lower):
                return "INELIGIBLE", 0.0, "Degree explicitly restricted to Computer Science / IT only"

        # Higher degree mandatory requirement (M.Tech/MS/Ph.D only with no B.Tech)
        higher_only_patterns = [
            r"\bmust\s+have\s+(?:a\s+)?(?:ph\.?d|doctorate)\b",
            r"\brequires\s+(?:a\s+)?(?:ph\.?d|master'?s\s+degree\s+only)\b"
        ]
        for hpo in higher_only_patterns:
            if re.search(hpo, text_lower):
                return "INELIGIBLE", 0.0, "Requires mandatory PhD or Master's degree"

        # Explicit acceptance of Any Engineering / Circuit / Electrical
        accept_patterns = [
            r"\b(?:any\s+(?:engineering\s+)?discipline|any\s+(?:engineering\s+)?branch|all\s+branches|all\s+engineering\s+disciplines)\b",
            r"\b(?:b\.?tech|b\.?e\.?|bachelor'?s?)[\w\s]{0,15}any\s*(?:engineering\s*)?branch\b",
            r"\b(?:electrical|eee|electrical\s+and\s+electronics|circuit\s+branches)\b",
            r"\b(?:b\.?tech|b\.?e\.?|bachelor'?s?)\s+in\s+(?:computer\s+science|it|electrical|electronics|related\s+field|relevant\s+technical\s+field)\b",
            r"\bor\s+equivalent\s+(?:practical\s+)?experience\b"
        ]
        for pat in accept_patterns:
            if re.search(pat, text_lower):
                return "ELIGIBLE", 20.0, "Degree criteria explicitly accepts Electrical Engineering / related engineering disciplines"

        # General technical degree mention without excluding EE
        if re.search(r"\b(?:b\.?tech|b\.?e\.?|bachelor'?s?\s+degree)\b", text_lower):
            return "ELIGIBLE", 18.0, "Accepts B.Tech / Bachelor's in engineering without branch restrictions"

        return "UNKNOWN", 10.0, "Specific engineering branch requirements are unstated"

    def classify_graduation_eligibility(self, text: str) -> Tuple[str, float, str]:
        """
        Evaluates graduation batch eligibility (Candidate is 2026 Batch).
        Returns (verdict: 'ELIGIBLE' | 'INELIGIBLE' | 'UNKNOWN', score_points, reason).
        """
        text_lower = text.lower()
        if not text_lower:
            return "UNKNOWN", 8.0, "Graduation year criteria unstated"

        grad_year = self.candidate.get("graduation_year", 2026)
        eligible_years = self.candidate.get("eligible_graduation_years", [2025, 2026, 2027])

        # Batch explicit exclusions (e.g., 2023 batch only, 2024 batch only)
        past_batches_only = [
            r"\b(?:2021|2022|2023|2024)\s+(?:batch|graduates?|passouts?)\s+only\b",
            r"\bonly\s+(?:for\s+)?(?:2021|2022|2023|2024)\s+(?:batch|graduates?|passouts?)\b"
        ]
        for pbo in past_batches_only:
            if re.search(pbo, text_lower):
                return "INELIGIBLE", 0.0, "Restricted exclusively to earlier graduation batches"

        # 2nd or 3rd year only internship (excluding final year 2026)
        if re.search(r"\b(?:pre[\s-]?final\s+year|2nd\s+year|3rd\s+year)\s+students?\s+only\b", text_lower):
            return "INELIGIBLE", 0.0, "Restricted exclusively to pre-final or junior year students"

        # Explicit match for 2026 / 2025-2026 / final year
        for yr in eligible_years:
            if re.search(rf"\b{yr}\b", text_lower):
                return "ELIGIBLE", 15.0, f"Explicitly mentions eligible graduation batch {yr}"

        # Final year / new grad patterns
        if re.search(r"(?<!pre-)(?<!pre\s)\bfinal\s+year\b", text_lower) or re.search(r"\bnew\s+grad(?:uate)?\b", text_lower):
            return "ELIGIBLE", 14.0, "Explicitly open to final year / new graduate candidates"

        return "UNKNOWN", 8.0, "Graduation batch unstated (compatible with 2026 batch)"

    def classify_experience_eligibility(self, text: str) -> Tuple[str, float, str]:
        """
        Evaluates experience requirements (Candidate has 0 years full-time software experience).
        Returns (verdict: 'ELIGIBLE' | 'INELIGIBLE' | 'UNKNOWN', score_points, reason).
        """
        text_lower = text.lower()
        if not text_lower:
            return "UNKNOWN", 8.0, "Experience criteria unstated"

        # Check for 0-2 years (Borderline acceptable for freshers)
        if re.search(r"\b0\s*(?:to|-)\s*2\s+years?(?:\s+of)?(?:\s+relevant|\s+work)?\s+experience\b", text_lower):
            return "ELIGIBLE", 12.0, "Requires 0-2 years experience (borderline/fresher friendly)"

        # Check for mandatory 2+ / 3+ / 5+ years experience
        disqualifying_exp_patterns = [
            r"\b([2-9]|\d{2,})\s*(?:\+|plus)?\s*years?(?:\s+(?:of|relevant|professional|industry|software|full-time|prior|hands-on|work|engineering|commercial))*\s+experience\b",
            r"\bminimum\s+(?:of\s+)?([2-9]|\d{2,})\s+years?\b",
            r"\bat\s+least\s+([2-9]|\d{2,})\s+years?\b",
            r"\b([2-9]|\d{2,})\s*(?:to|-)\s*\d+\s+years?(?:\s+(?:of|relevant|professional|industry|software|full-time|prior|hands-on|work|engineering|commercial))*\s+experience\b"
        ]
        for de in disqualifying_exp_patterns:
            m = re.search(de, text_lower)
            if m:
                # Ensure it's not preceded by "preferred" or "nice to have"
                start = max(0, m.start() - 30)
                context = text_lower[start:m.start()]
                if "preferred" not in context and "plus" not in context and "bonus" not in context:
                    return "INELIGIBLE", 0.0, f"Requires mandatory professional industry experience: '{m.group(0)}'"

        # Explicit fresher / 0 years / intern patterns
        fresher_patterns = [
            r"\b0\s*(?:to|-)\s*1\s+(?:years?|yrs?)(?:\s+of)?(?:\s+experience)?\b",
            r"\b(?:0\s+years?|0\s+yrs?|no\s+prior\s+experience|freshers?(?:\s+welcome)?|entry[\s-]level|recent\s+graduates?|graduate\s+trainee)\b",
            r"\binternship\b"
        ]
        for fp in fresher_patterns:
            if re.search(fp, text_lower):
                return "ELIGIBLE", 15.0, "Explicitly accepts 0-1 years / freshers / interns"

        return "UNKNOWN", 8.0, "Experience requirements unstated"

    def classify_location_eligibility(self, location_text: str, full_text: str = "") -> Tuple[str, float, str]:
        """
        Evaluates India location eligibility according to Part 2 specifications.
        Returns (verdict: 'INDIA' | 'OUTSIDE_INDIA' | 'UNKNOWN', score_points, reason).
        """
        loc_str = location_text.lower() if location_text else ""
        desc_lower = full_text.lower() if full_text else ""

        # 1. India Cities and Regions in location text
        india_cities = [
            "india", "bengaluru", "bangalore", "hyderabad", "pune", "chennai", "mumbai",
            "delhi", "noida", "gurgaon", "gurugram", "kolkata", "ahmedabad", "jaipur", "patna"
        ]
        for city in india_cities:
            if re.search(rf"\b{re.escape(city)}\b", loc_str):
                return "INDIA", 10.0, f"Location verified in India: '{city.title()}'"

        # 2. Definite Foreign Locations (US, UK, Europe, etc.) -> OUTSIDE_INDIA
        foreign_indicators = [
            "united states", "usa", "u.s.", "canada", "united kingdom", "london", "germany",
            "singapore", "australia", "poland", "warsaw", "montreal", "toronto", "vancouver",
            "ireland", "dublin", "france", "paris", "netherlands", "amsterdam", "switzerland",
            "zurich", "san francisco", "new york", "seattle", "austin", "chicago", "boston"
        ]
        for f_ind in foreign_indicators:
            if re.search(rf"\b{re.escape(f_ind)}\b", loc_str):
                return "OUTSIDE_INDIA", 0.0, f"Location is outside India: '{location_text}'"

        # 3. Remote Position check
        if "remote" in loc_str:
            # Reject if restricted to US/Europe/Americas
            if re.search(r"\b(?:us\s+only|usa\s+only|united\s+states\s+only|emea\s+only|north\s+america|americas)\b", f"{loc_str} {desc_lower}"):
                return "OUTSIDE_INDIA", 0.0, "Remote position restricted to non-India regions"
            # If explicit India remote
            if any(c in loc_str or c in desc_lower for c in ["india", "apac", "worldwide", "anywhere"]):
                return "INDIA", 9.0, "Remote position eligible for candidates in India"
            return "UNKNOWN", 5.0, "Remote position without confirmed India eligibility"

        # 4. Check description for India cities if location_text was empty
        for city in india_cities:
            if re.search(rf"\b{re.escape(city)}\b", desc_lower):
                return "INDIA", 8.0, f"Location inferred in India from posting details: '{city.title()}'"

        return "UNKNOWN", 5.0, "Location unstated or unverified"

    def classify_compensation(self, text: str, employment_type: str = "Full-time") -> Tuple[str, str, Dict[str, str]]:
        """
        Evaluates compensation status according to Hunter 4.0 specifications.
        Returns (status: '12_LPA_OR_ABOVE' | 'BELOW_12_LPA' | 'UNDISCLOSED' | 'NOT_APPLICABLE', display_text, details_dict).
        """
        details = {
            "base_salary": "", "variable_comp": "", "joining_bonus": "",
            "stock_equity": "", "total_ctc": ""
        }
        text_lower = text.lower() if text else ""
        if not text_lower:
            return "UNDISCLOSED", "Not disclosed", details

        # Check for INR LPA patterns
        lpa_match = re.search(r"(?:(?:inr|rs\.?|₹)\s*)?(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lac|lacs)", text_lower)
        if lpa_match:
            val = float(lpa_match.group(1))
            disp = f"₹{val:.1f} LPA"
            details["total_ctc"] = disp
            if val >= 12.0:
                return "12_LPA_OR_ABOVE", disp, details
            else:
                return "BELOW_12_LPA", disp, details

        # Check for Monthly Stipend (Internships)
        stipend_match = re.search(r"(?:(?:inr|rs\.?|₹)\s*)?(\d{2,3}(?:,\d{3})?|\d{4,6})\s*(?:/\s*(?:month|mo|pm)|per\s+month)", text_lower)
        if stipend_match:
            raw_num = stipend_match.group(1).replace(",", "")
            disp = f"₹{int(raw_num):,}/month"
            details["base_salary"] = disp
            return "UNDISCLOSED", disp, details

        return "UNDISCLOSED", "Not disclosed", details

    def evaluate_skills(self, text: str) -> Tuple[float, List[str]]:
        """Scores candidate skills alignment (up to 10 points)."""
        candidate_skills = self.candidate.get("technical_skills", [])
        text_lower = text.lower() if text else ""
        found = []
        for sk in candidate_skills:
            if re.search(rf"\b{re.escape(sk.lower())}\b", text_lower):
                found.append(sk)
        score = min(10.0, len(found) * 2.0)
        return score, found

    def evaluate_job(self, job_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs full 7-dimension eligibility evaluation and 100-point scoring.
        Returns structured evaluation dictionary with classification, match_score, reasons, and notes.
        """
        title = job_dict.get("title", "")
        desc = job_dict.get("description", "")
        loc = job_dict.get("location", "")
        emp_type = job_dict.get("employment_type", "Full-time")
        app_status = job_dict.get("application_status", "OPEN")

        # 1. Role Relevance
        role_rel, r_score, r_reason = self.classify_role_relevance(title, desc)

        # 2. Degree Eligibility
        deg_el, deg_score, deg_reason = self.classify_degree_eligibility(desc)

        # 3. Graduation Eligibility
        grad_el, grad_score, grad_reason = self.classify_graduation_eligibility(f"{title} {desc}")

        # 4. Experience Eligibility
        exp_el, exp_score, exp_reason = self.classify_experience_eligibility(f"{title} {desc}")

        # 5. Location Eligibility
        loc_el, loc_score, loc_reason = self.classify_location_eligibility(loc, desc)

        # 6. Skills Match
        skills_score, matched_skills = self.evaluate_skills(f"{title} {desc}")

        # 7. Employment Type Preference (5 pts)
        emp_score = 5.0 if emp_type in ["Full-time", "Internship", "PPO"] else 2.0

        # Compensation
        comp_status, comp_disp, comp_details = self.classify_compensation(desc, emp_type)

        total_score = r_score + deg_score + grad_score + exp_score + loc_score + skills_score + emp_score

        score_reasons = {
            "role_relevance": {"score": r_score, "reason": r_reason},
            "degree_eligibility": {"score": deg_score, "reason": deg_reason},
            "graduation_eligibility": {"score": grad_score, "reason": grad_reason},
            "experience_eligibility": {"score": exp_score, "reason": exp_reason},
            "location_eligibility": {"score": loc_score, "reason": loc_reason},
            "skills_match": {"score": skills_score, "matched_skills": matched_skills},
            "employment_type": {"score": emp_score, "type": emp_type}
        }

        # Hard Rejection Gate Check
        disqualifications = []
        if role_rel == "REJECTED":
            disqualifications.append(r_reason)
        if deg_el == "INELIGIBLE":
            disqualifications.append(deg_reason)
        if grad_el == "INELIGIBLE":
            disqualifications.append(grad_reason)
        if exp_el == "INELIGIBLE":
            disqualifications.append(exp_reason)
        if loc_el == "OUTSIDE_INDIA":
            disqualifications.append(loc_reason)
        if app_status == "CLOSED":
            disqualifications.append("Application is verified as closed")

        if disqualifications:
            classification = "REJECTED"
            eligibility_notes = "; ".join(disqualifications)
        else:
            # Verified Match criteria:
            # Role is MATCH, Degree is ELIGIBLE, Location is INDIA, Exp is ELIGIBLE, Status is OPEN, Score >= 75
            is_verified = (
                role_rel == "MATCH" and
                deg_el == "ELIGIBLE" and
                exp_el == "ELIGIBLE" and
                loc_el == "INDIA" and
                app_status == "OPEN" and
                total_score >= self.thresholds.get("verified_match_min_score", 75)
            )
            if is_verified:
                classification = "VERIFIED MATCH"
                eligibility_notes = f"Verified Fresher Software/AI Match (Score {total_score:.1f}/100)"
            else:
                classification = "POTENTIAL MATCH"
                unknowns = []
                if deg_el == "UNKNOWN":
                    unknowns.append("Degree requirements unstated")
                if grad_el == "UNKNOWN":
                    unknowns.append("Graduation batch unstated")
                if exp_el == "UNKNOWN":
                    unknowns.append("Exact years of experience unstated")
                if loc_el == "UNKNOWN":
                    unknowns.append("Location unverified")
                eligibility_notes = "Review required: " + (", ".join(unknowns) if unknowns else "Borderline score / requirements")

        return {
            "classification": classification,
            "match_score": round(total_score, 1),
            "role_relevance": role_rel,
            "degree_eligibility": deg_el,
            "graduation_eligibility": grad_el,
            "experience_eligibility": exp_el,
            "location_eligibility": loc_el,
            "application_status": app_status,
            "compensation_status": comp_status,
            "compensation_text": comp_disp,
            "base_salary": comp_details.get("base_salary", ""),
            "variable_comp": comp_details.get("variable_comp", ""),
            "joining_bonus": comp_details.get("joining_bonus", ""),
            "stock_equity": comp_details.get("stock_equity", ""),
            "total_ctc": comp_details.get("total_ctc", ""),
            "eligibility_notes": eligibility_notes,
            "score_reasons": score_reasons
        }
