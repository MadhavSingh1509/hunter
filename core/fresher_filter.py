"""
Hunter — Strict Fresher Software Engineering & AI/ML Job Filter
Candidate Profile: B.Tech Electrical Engineering (EE), Graduating 2027, 0 years full-time software industry experience.
Location: India only (or Remote explicitly open to India).

Core Principle:
"If the job's fresher eligibility cannot be established, do not include it in my email.
I prefer fewer genuine fresher openings over hundreds of irrelevant jobs."
"""

import re
import html
from dataclasses import dataclass, field
from typing import Tuple, List, Optional


@dataclass
class FilterDecision:
    is_eligible: bool
    reason: str
    positive_signals: List[str] = field(default_factory=list)


class StrictFresherFilter:
    """
    Deterministic, description-reading filter for genuine India-based fresher
    Software Engineering & AI/ML roles for a B.Tech Electrical Engineering (2027) candidate.
    """

    # 1. Hard Seniority / Experience-Level Title Exclusions
    SENIOR_TITLE_PATTERNS = [
        r"\bsenior\b", r"\bsr\.?\b", r"\bstaff\b", r"\bprincipal\b",
        r"\blead\b", r"\btech\s+lead\b", r"\bteam\s+lead\b",
        r"\bmanager\b", r"\bdirector\b", r"\bvp\b", r"\bavp\b", r"\bsvp\b",
        r"\bhead\s+of\b", r"\bchief\b", r"\barchitect\b", r"\bdistinguished\b",
        r"\bfellow\b", r"\bexecutive\b", r"\bexperienced\b", r"\bmid[\s-]?level\b",
        r"\bsde[\s-]?(?:ii|iii|iv|2|3|4)\b",
        r"\bsoftware\s+(?:development\s+)?engineer[\s-]?(?:ii|iii|iv|2|3|4)\b",
        r"\bengineer[\s-]?(?:ii|iii|iv|2|3|4)\b",
        r"\bdeveloper[\s-]?(?:ii|iii|iv|2|3|4)\b",
        r"\b(?:ii|iii|iv)\b(?=\s*[-,(/]|$)",
        r"\b(?:l4|l5|l6|l7|l8|ic3|ic4|ic5|ic6|e4|e5|e6)\b",
        r"\b(?:smts|lmts|pmts|mts[\s-]?[234])\b",
        r"\blevel\s+[2-9]\b", r"\bgrade\s+[5-9]\b",
        r"\bmember\s+of\s+technical\s+staff\s*(?:ii|iii|2|3)\b",
    ]

    # 2. Hard Non-Software / Non-AI Title Exclusions
    NON_TECH_TITLE_PATTERNS = [
        r"\bsales\b", r"\baccount\s+executive\b", r"\bbusiness\s+development\b",
        r"\brecruiter\b", r"\btalent\s+acquisition\b", r"\bhuman\s+resources\b", r"\bhr\b",
        r"\bmarketing\b", r"\bfinance\b", r"\baccounting\b", r"\baccountant\b",
        r"\btax\b", r"\baudit\b", r"\blegal\b", r"\bcounsel\b", r"\battorney\b",
        r"\bcustomer\s+support\b", r"\btechnical\s+support\b", r"\bsupport\s+engineer\b",
        r"\bhelpdesk\b", r"\bservice\s+desk\b", r"\bcall\s+center\b",
        r"\bproduct\s+manager\b", r"\bprogram\s+manager\b", r"\bproject\s+manager\b",
        r"\bscrum\s+master\b", r"\boperations\s+executive\b", r"\bsupply\s+chain\b",
        r"\bprocurement\b", r"\blogistics\b", r"\bcopywriter\b", r"\bgraphic\s+designer\b",
        r"\bux\s+designer\b", r"\bui\s+designer\b", r"\bproduct\s+designer\b",
        r"\bcompliance\b", r"\bvaluations\b", r"\bcontroller\b", r"\btrader\b",
        r"\bpayroll\b", r"\bcollections\b", r"\bunderwriter\b", r"\bactuar",
        r"\bfacilities\b", r"\breceptionist\b", r"\badmin\s+assistant\b",
        r"\bsolutions?\s+consultant\b", r"\bdelivery\s+consultant\b",
        r"\btechnical\s+writer\b", r"\bcontent\s+writer\b", r"\bcontent\s+moderator\b",
        # Core Electrical / Mechanical / Civil / Non-SW Hardware exclusions
        r"\bsubstation\b", r"\bpower\s+systems?\b", r"\btransformer\b", r"\bswitchgear\b",
        r"\belectrician\b", r"\bhigh\s+voltage\b", r"\bpower\s+plant\b", r"\bwiring\b",
        r"\bmechanical\s+engineer\b", r"\bcivil\s+engineer\b", r"\bchemical\s+engineer\b",
        r"\bphysical\s+design\b", r"\banalog\s+design\b", r"\bpcb\s+design\b",
        r"\bmanufacturing\s+engineer\b", r"\bprocess\s+engineer\b", r"\bfield\s+engineer\b",
        r"\bsilicon\s+validation\b", r"\bmask\s+design\b", r"\blayout\s+engineer\b",
        r"\bproduction\s+support\b", r"\bapplication\s+support\b",
    ]

    # 3. Target Software Engineering & AI/ML Role Title Patterns (Section 4)
    TARGET_ROLE_PATTERNS = [
        # Software Engineering
        r"\bsoftware\s+development\s+engineer\b",
        r"\bsoftware\s+dev(?:elopment)?\s+eng(?:ineer)?\b",
        r"\bsoftware\s+engineer\b",
        r"\bsoftware\s+developer\b",
        r"\bsde\b",
        r"\bbackend\s+(?:software\s+)?(?:engineer|developer)\b",
        r"\bback[\s-]?end\s+(?:engineer|developer)\b",
        r"\bfrontend\s+(?:software\s+)?(?:engineer|developer)\b",
        r"\bfront[\s-]?end\s+(?:engineer|developer)\b",
        r"\bfull[\s-]?stack\s+(?:software\s+)?(?:engineer|developer)\b",
        r"\bapplication\s+developer\b",
        r"\bapplication\s+development\s+associate\b",
        r"\b(?:java|python|c\+\+|golang|node\.?js|react|javascript|typescript|scala|rust)\s+(?:software\s+)?(?:engineer|developer)\b",
        r"\bplatform\s+engineer\b",
        r"\bcloud\s+(?:software\s+)?engineer\b",
        r"\binfrastructure\s+(?:software\s+)?engineer\b",
        r"\bdevops\s+engineer\b",
        r"\bsite\s+reliability\s+engineer\b",
        r"\bsre\b",
        r"\bsystems?\s+software\s+engineer\b",
        r"\bembedded\s+software\s+engineer\b",
        r"\bfirmware\s+(?:software\s+)?engineer\b",
        r"\bapi\s+engineer\b",
        r"\bweb\s+developer\b",
        r"\bmobile\s+(?:software\s+)?(?:engineer|developer)\b",
        r"\b(?:android|ios)\s+(?:software\s+)?(?:engineer|developer)\b",
        r"\bgraduate\s+software\s+engineer\b",
        r"\bgraduate\s+engineer\b",
        r"\bgraduate\s+trainee\b",
        r"\bassociate\s+software\s+engineer\b",
        r"\bsoftware\s+(?:engineering\s+)?(?:intern|internship|trainee|apprentice)\b",
        r"\bsoftware\s+development\s+(?:intern|internship)\b",
        r"\btechnology\s+(?:intern|analyst|graduate)\b",
        r"\bengineering\s+intern\b",
        r"\bdeveloper\s+intern\b",
        # AI / ML Engineering
        r"\bai\s+(?:software\s+)?engineer\b",
        r"\bai\s+developer\b",
        r"\bmachine\s+learning\s+(?:software\s+)?engineer\b",
        r"\bml\s+(?:software\s+|platform\s+)?engineer\b",
        r"\bapplied\s+(?:ai|ml|machine\s+learning)\s+engineer\b",
        r"\bgenerative\s+ai\s+engineer\b",
        r"\bgenai\s+engineer\b",
        r"\bllm\s+engineer\b",
        r"\bnlp\s+engineer\b",
        r"\bdeep\s+learning\s+engineer\b",
        r"\bcomputer\s+vision\s+engineer\b",
        r"\bai\s*/\s*ml\s+(?:engineer|developer|intern|internship|software\s+engineer)\b",
        r"\b(?:ai|ml|machine\s+learning|deep\s+learning|nlp|genai)\s+(?:intern|internship)\b",
        r"\bapplied\s+scientist\s+intern\b",
        r"\bresearch\s+engineer\s+intern\b",
    ]

    # 4. Higher-degree-only title exclusions (PhD / Master's / MBA exclusive)
    HIGHER_DEGREE_TITLE_PATTERNS = [
        r"\bph\.?d\.?\b", r"\bdoctorate\b", r"\bpostdoc\b",
        r"\bmaster'?s\b", r"\bm\.?tech\s+only\b", r"\bmba\b",
    ]

    # 5. India Location Indicators
    INDIA_LOCATIONS = [
        "india", "bengaluru", "bangalore", "hyderabad", "pune", "chennai",
        "mumbai", "delhi", "ncr", "noida", "gurgaon", "gurugram", "kolkata",
        "ahmedabad", "jaipur", "patna", "kochi", "cochin", "trivandrum",
        "thiruvananthapuram", "coimbatore", "indore", "chandigarh", "mysore",
        "mysuru", "visakhapatnam", "bhubaneswar", "mangalore", "nagpur",
        "vadodara", "surat", "lucknow", "mohali", "secunderabad", "navi mumbai",
        "thane", "karnataka", "telangana", "maharashtra", "tamil nadu",
        "haryana", "uttar pradesh", "west bengal", "gujarat", "kerala",
    ]

    # 6. Foreign Location Indicators (when no India city is present)
    FOREIGN_LOCATIONS = [
        "united states", "usa", "u.s.", "u.s.a", "canada", "united kingdom",
        "london", "manchester", "glasgow", "edinburgh", "knutsford",
        "germany", "berlin", "munich", "frankfurt", "singapore", "australia",
        "sydney", "melbourne", "poland", "warsaw", "krakow", "montreal",
        "toronto", "vancouver", "ireland", "dublin", "france", "paris",
        "netherlands", "amsterdam", "switzerland", "zurich", "japan", "tokyo",
        "china", "beijing", "shanghai", "korea", "seoul", "israel", "tel aviv",
        "brazil", "sao paulo", "mexico", "spain", "madrid", "barcelona",
        "italy", "milan", "sweden", "stockholm", "romania", "bucharest",
        "czech", "prague", "hungary", "budapest", "philippines", "manila",
        "taiwan", "taipei", "hong kong", "vietnam", "malaysia", "kuala lumpur",
        "uae", "dubai", "san francisco", "new york", "seattle", "austin",
        "chicago", "boston", "los angeles", "atlanta", "dallas", "denver",
        "san jose", "santa clara", "mountain view", "palo alto", "sunnyvale",
        "redmond", "bellevue", "cupertino", "menlo park", "california",
        "texas", "washington", "virginia", "massachusetts", "new jersey",
        "north carolina", "georgia", "illinois", "colorado", "oregon",
        "arizona", "utah", "florida", "ohio", "pennsylvania", "michigan",
    ]

    def __init__(self, graduation_year: int = 2027):
        self.graduation_year = graduation_year

    @staticmethod
    def clean_text(raw: str) -> str:
        """Strips HTML tags, unescapes entities, and normalizes whitespace."""
        if not raw:
            return ""
        text = html.unescape(raw)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def check_location(self, location: str, title: str = "", description: str = "") -> Tuple[bool, str]:
        """Strict India-only location filter."""
        loc_lower = self.clean_text(location).lower()
        title_lower = self.clean_text(title).lower()

        # Check explicit India city/state/country in location field or title
        for city in self.INDIA_LOCATIONS:
            if re.search(rf"\b{re.escape(city)}\b", loc_lower):
                return True, f"India location: {city}"

        # Special code check for ", IND" or "IND," or "(IND)"
        if re.search(r"(?:^|[\s,(-])ind(?:$|[\s,)-])", loc_lower):
            return True, "India country code (IND)"

        # Check if location explicitly names a foreign country/city
        for f in self.FOREIGN_LOCATIONS:
            if re.search(rf"\b{re.escape(f)}\b", loc_lower):
                return False, f"Outside India ({location})"

        # Check title for foreign city (e.g. "Intern Software Developer - Warsaw 2027")
        for f in self.FOREIGN_LOCATIONS:
            if re.search(rf"\b{re.escape(f)}\b", title_lower):
                return False, f"Title specifies foreign location ({f})"

        # Check Remote: ONLY accept if India is explicitly eligible
        if "remote" in loc_lower:
            desc_lower = self.clean_text(description).lower()
            combined = f"{loc_lower} {desc_lower}"
            if re.search(r"\b(?:us\s+only|usa\s+only|united\s+states\s+only|emea\s+only|north\s+america|europe\s+only|uk\s+only)\b", combined):
                return False, "Remote restricted outside India"
            if any(re.search(rf"\b{re.escape(c)}\b", combined) for c in ["india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi"]):
                return True, "Remote eligible for India"
            return False, "Remote without confirmed India eligibility"

        # If location was empty, check title for India city
        for city in self.INDIA_LOCATIONS:
            if re.search(rf"\b{re.escape(city)}\b", title_lower):
                return True, f"India location in title: {city}"

        return False, f"Location not confirmed as India ('{location}')"

    def check_role(self, title: str) -> Tuple[bool, str]:
        """Strict Software Engineering & AI/ML role filter + Seniority exclusion."""
        t = self.clean_text(title).lower()
        if not t:
            return False, "Empty job title"

        # Reject senior / experienced levels
        for pat in self.SENIOR_TITLE_PATTERNS:
            if re.search(pat, t):
                return False, f"Senior/mid-level title excluded ({pat})"

        # Reject higher-degree-only titles (PhD / Master's / MBA)
        for pat in self.HIGHER_DEGREE_TITLE_PATTERNS:
            if re.search(pat, t):
                return False, f"Higher-degree-only title ({pat})"

        # Reject non-software / non-AI roles
        for pat in self.NON_TECH_TITLE_PATTERNS:
            if re.search(pat, t):
                return False, f"Non-software/non-AI role ({pat})"

        # Must match target SWE or AI/ML role patterns
        for pat in self.TARGET_ROLE_PATTERNS:
            if re.search(pat, t):
                return True, f"Matches target role ({pat})"

        return False, "Title is not a target Software Engineering or AI/ML role"

    def check_degree_and_branch(self, description: str) -> Tuple[bool, str]:
        """Checks Electrical Engineering (B.Tech EE) eligibility."""
        d = self.clean_text(description).lower()
        if not d:
            return True, "No degree restrictions found"

        # Reject CSE/IT only (explicitly excluding Electrical Engineering)
        cs_only_patterns = [
            r"\b(?:only|strictly|exclusively)\s+(?:for\s+|open\s+to\s+)?(?:computer\s+science|cse|cs/it|cse/it|cs\s+and\s+it|information\s+technology)\b",
            r"\b(?:computer\s+science|cse|cs/it|cse/it)\s+(?:only|graduates?\s+only|students?\s+only|branch\s+only|candidates?\s+only)\b",
            r"\brestricted\s+to\s+(?:computer\s+science|cse|it)\b",
            r"\b(?:b\.?tech|b\.?e\.?|degree)\s+in\s+(?:computer\s+science|cse)\s+only\b",
        ]
        for pat in cs_only_patterns:
            if re.search(pat, d):
                # Double check EE isn't explicitly listed alongside it
                if not re.search(r"\b(?:electrical|eee|all\s+branches|any\s+(?:engineering\s+)?branch|circuit\s+branches)\b", d):
                    return False, "Explicitly restricted to Computer Science / IT (excludes Electrical Engineering)"

        # Reject mandatory PhD or Master's-only when Bachelor's/B.Tech is not accepted
        has_bachelors = bool(re.search(r"\b(?:b\.?tech|b\.?e\.?|bachelor'?s?|undergraduate|b\.?s\.?|bs\b)\b", d))
        if re.search(r"\b(?:must\s+(?:have|hold|be\s+pursuing)\s+a?\s*(?:ph\.?d|doctorate)|ph\.?d\.?\s+(?:is\s+)?required|currently\s+enrolled\s+in\s+a\s+ph\.?d)\b", d):
            if not has_bachelors:
                return False, "Requires PhD / Doctorate"
        if re.search(r"\b(?:must\s+have\s+a?\s*master'?s\s+degree|master'?s\s+degree\s+(?:is\s+)?required|m\.?tech\s+only|currently\s+enrolled\s+in\s+a\s+master'?s)\b", d):
            if not has_bachelors:
                return False, "Requires Master's degree (B.Tech not listed)"

        return True, "B.Tech Electrical Engineering eligible"

    def check_graduation_year(self, title: str, description: str) -> Tuple[bool, str]:
        """Checks graduation batch eligibility for 2027 B.Tech fresher."""
        combined = self.clean_text(f"{title} {description}").lower()

        # Check explicit past-batch-only restrictions that exclude 2027 (e.g. 2023/2024/2025 only)
        past_only_patterns = [
            r"\b(?:2021|2022|2023|2024|2025)\s*(?:batch|graduates?|pass[\s-]?outs?|class)(?:\s+(?:graduates?|students?|candidates?))?\s+only\b",
            r"\b(?:only|strictly)\s+(?:for\s+)?(?:2021|2022|2023|2024|2025)\s*(?:batch|graduates?|pass[\s-]?outs?)\b",
            r"\bgraduating\s+(?:in\s+)?(?:2022|2023|2024|2025)\s+only\b",
            r"\bmust\s+have\s+graduated\s+in\s+(?:2021|2022|2023|2024|2025)\b",
        ]
        for pat in past_only_patterns:
            if re.search(pat, combined) and "2027" not in combined:
                return False, "Restricted to earlier graduation batch (excludes 2027)"

        # Also check "Class of 2024" / "Class of 2025" when 2027 is NOT mentioned
        if re.search(r"\b(?:class\s+of|batch\s+of)\s+(?:2022|2023|2024|2025)\b", combined) and "2027" not in combined and "2026" not in combined:
            return False, "Restricted to earlier graduation class (excludes 2027)"

        return True, "Graduation year compatible with 2027"

    def split_required_vs_preferred(self, text: str) -> str:
        """
        Extracts the required/basic qualifications portion so 'Preferred Qualifications'
        doesn't falsely reject a fresher role, while 'Basic/Minimum Qualifications' is strictly enforced.
        """
        # Cut off at Preferred Qualifications / Nice to Have / Good to Have / Bonus section if clearly delineated
        m = re.search(
            r"\b(?:preferred\s+qualifications?|nice\s+to\s+have|good\s+to\s+have|desired\s+qualifications?|bonus\s+qualifications?)\s*:?",
            text,
            re.IGNORECASE
        )
        if m and m.start() > 120:
            return text[:m.start()]
        return text

    def check_fresher_experience(self, title: str, description: str) -> Tuple[bool, str, List[str]]:
        """
        STRICT FRESHER CHECK (Section 3):
        1. Rejects ANY mandatory 2+ years OR mandatory 1+ years of non-internship/full-time/professional experience.
        2. Requires POSITIVE confirmation that the role is for freshers / new grads / interns / 0-1 yrs / 0-2 yrs (fresher eligible).
        3. If fresher eligibility CANNOT be established, REJECTS the job.
        """
        title_clean = self.clean_text(title).lower()
        desc_clean = self.clean_text(description).lower()
        required_desc = self.split_required_vs_preferred(desc_clean)
        full_text = f"{title_clean} {desc_clean}"

        # --- STEP A: HARD EXPERIENCE DISQUALIFIERS (in title AND required qualifications) ---

        # 0. Reject explicit multi-year experience ranges in TITLE (e.g. "(5-9 Years)", "- 4+ years")
        masked_title = re.sub(r"\b0\s*(?:-|–|to)\s*[12]\s*(?:years?|yrs?)\b", " ZERO_TO_TWO_YRS ", title_clean)
        m_title_exp = re.search(r"\b(?:([2-9]|\d{2,})\s*(?:\+|(?:-|–|to)\s*\d+)?|1\s*\+)\s*(?:years?|yrs?)\b", masked_title)
        if m_title_exp:
            return False, f"Title requires experienced candidate: '{m_title_exp.group(0)}'", []

        # 1. Explicit "non-internship" 1+ / 2+ / 3+ years (classic Amazon/Big Tech SDE trap!)
        m_non_intern = re.search(
            r"\b([1-9]|\d{2,})\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?non[\s-]?internship\b",
            required_desc
        )
        if m_non_intern:
            return False, f"Requires mandatory non-internship experience: '{m_non_intern.group(0)}'", []

        # 1b. Explicit "Bachelor's + N years" (e.g. Cisco: "Bachelor's degree + 5 years ... OR Ph.D. + 0 years")
        m_bachelor_exp = re.search(
            r"\b(?:bachelor'?s?|b\.?s\.?|b\.?tech|b\.?e\.?)(?:\s+degree)?\s*(?:\+|with|and|,)\s*([1-9]|\d{2,})\s*\+?\s*(?:years?|yrs?)\b",
            required_desc
        )
        if m_bachelor_exp:
            return False, f"Requires Bachelor's + prior experience: '{m_bachelor_exp.group(0)}'", []

        # 2. Mandatory 2+ / 3+ / 4+ / 5+ years of experience (NOT 0-2 years!)
        # First temporarily mask "0-2 years" / "0 to 2 years" / "0 - 1 years" so it doesn't match "2 years"
        masked_req = re.sub(r"\b0\s*(?:-|–|to)\s*[12]\s*(?:years?|yrs?)\b", " ZERO_TO_TWO_YRS ", required_desc)

        hard_2plus_patterns = [
            r"\b([2-9]|\d{2,})\s*\+\s*(?:years?|yrs?)\b",
            r"\b([2-9]|\d{2,})\s*(?:-|–|to)\s*\d+\s*(?:years?|yrs?)\s+(?:of\s+)?(?:[\w/,-]+\s+){0,5}experience\b",
            r"\b(?:minimum|at\s+least|min\.?|requires?|with)\s+(?:of\s+)?([2-9]|\d{2,})\s*\+?\s*(?:years?|yrs?)\b",
            r"\b([2-9]|\d{2,})\s+(?:years?|yrs?)\s+(?:of\s+)?(?:[\w/,-]+\s+){0,4}experience\b",
            r"\bexperience\s*[:\-]\s*([2-9]|\d{2,})\s*(?:\+|(?:-|–|to)\s*\d+)?\s*(?:years?|yrs?)\b",
        ]
        for pat in hard_2plus_patterns:
            m = re.search(pat, masked_req)
            if m:
                # Ignore if immediately preceded by "preferred" / "bonus" / "plus" or refers to company history ("over 20 years of experience in banking")
                prefix = masked_req[max(0, m.start() - 40):m.start()]
                if not any(w in prefix for w in ["preferred", "plus", "bonus", "desired", "ideally", "nice to have", "for over", "more than"]):
                    return False, f"Requires 2+ years mandatory experience: '{m.group(0)}'", []

        # Strip "Ph.D. + 0 years" / "Master's + 0-2 years" so higher-degree-only 0-year tracks NEVER count for B.Tech!
        fresher_check_desc = re.sub(
            r"\b(?:ph\.?d\.?|doctorate|master'?s?|m\.?s\.?|m\.?tech)\b[^.;\n]{0,25}\b0\s*(?:\+|(?:-|–|to)\s*[12])?\s*(?:years?|yrs?)",
            " HIGHER_DEGREE_ZERO_YRS ",
            required_desc
        )

        # 3. Mandatory 1+ years of full-time / professional / industry / work experience (when NOT explicitly 0-1 or fresher)
        has_explicit_0_or_fresher = bool(re.search(
            r"\b(?:0\s*(?:-|–|to)\s*[12]\s*(?:years?|yrs?)|0\s+years?|freshers?|fresh\s+grad|new\s+grad|university\s+grad|no\s+prior\s+experience|entry[\s-]?level)\b",
            f"{title_clean} {fresher_check_desc}"
        ))
        is_intern_title = bool(re.search(r"(?<!non-)(?<!non\s)\b(?:intern|internship|co-op|coop|apprentice)\b", title_clean))

        if not has_explicit_0_or_fresher and not is_intern_title:
            m_1plus = re.search(
                r"\b(?:1\s*\+|minimum\s+(?:of\s+)?1|at\s+least\s+1|1\s*(?:-|–|to)\s*[2-9])\s*(?:years?|yrs?)\s+(?:of\s+)?(?:[\w/,-]+\s+){0,4}(?:experience|software\s+development|engineering)\b",
                masked_req
            )
            if m_1plus:
                prefix = masked_req[max(0, m_1plus.start() - 35):m_1plus.start()]
                if not any(w in prefix for w in ["preferred", "plus", "bonus", "desired"]):
                    return False, f"Requires mandatory 1+ years professional experience: '{m_1plus.group(0)}'", []

        # --- STEP B: POSITIVE FRESHER CONFIRMATION (MANDATORY) ---
        positive_signals = []

        # Signal 1: Explicit Software/AI Internship in Title
        if is_intern_title:
            positive_signals.append("Internship role in title")

        # Signal 2: Explicit Fresher / New Grad / University / Campus / Entry-Level in Title
        strong_fresher_title = [
            (r"\bfreshers?\b", "Fresher in title"),
            (r"\bnew\s+grad(?:uate)?s?\b", "New Grad in title"),
            (r"\buniversity\s+grad(?:uate)?s?\b", "University Graduate in title"),
            (r"\brecent\s+grad(?:uate)?s?\b", "Recent Graduate in title"),
            (r"\bentry[\s-]?level\b", "Entry Level in title"),
            (r"\bcampus\b", "Campus hiring in title"),
            (r"\bgraduate\s+(?:software\s+)?engineer\b", "Graduate Software Engineer in title"),
            (r"\bgraduate\s+(?:engineer\s+)?trainee\b", "Graduate Engineer Trainee in title"),
            (r"\bjunior\s+(?:software\s+)?(?:engineer|developer)\b", "Junior Engineer in title"),
            (r"\b(?:early\s+career|early\s+talent)\b", "Early Career in title"),
            (r"\b202[67]\s+(?:grad|graduate|batch|intern|new\s+grad)\b", "2026/2027 batch in title"),
        ]
        for pat, label in strong_fresher_title:
            if re.search(pat, title_clean):
                positive_signals.append(label)

        # Signal 3: Explicit Fresher / 0-year / New Grad / Student eligibility in Description
        # NOTE: Uses fresher_check_desc so 'Ph.D. + 0 years' is excluded, and never matches 'non-internship'!
        strong_fresher_desc = [
            (r"\bfreshers?\b", "Freshers mentioned in JD"),
            (r"\bfresh\s+graduates?\b", "Fresh graduates in JD"),
            (r"\bnew\s+(?:college\s+)?grad(?:uate)?s?\b", "New grad in JD"),
            (r"\buniversity\s+grad(?:uate)?s?\b", "University graduate in JD"),
            (r"\brecent\s+grad(?:uate)?s?\b", "Recent graduate in JD"),
            (r"\bentry[\s-]?level\b", "Entry-level in JD"),
            (r"\bearly[\s-]?(?:in[\s-]?)?career\b", "Early career in JD"),
            (r"\b0\s*(?:-|–|to)\s*1\s*(?:years?|yrs?)\b", "0-1 years experience in JD"),
            (r"\b0\s*(?:-|–|to)\s*2\s*(?:years?|yrs?)\b", "0-2 years experience in JD"),
            (r"\b0\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:[\w-]+\s+){0,2}experience\b", "0 years experience in JD"),
            (r"\bno\s+prior\s+(?:work\s+|industry\s+)?experience\b", "No prior experience required"),
            (r"\bcurrently\s+(?:enrolled|pursuing)\s+(?:a\s+)?(?:b\.?tech|b\.?e\.?|bachelor|undergraduate|degree)\b", "Currently pursuing Bachelor's in JD"),
            (r"\bgraduating\s+in\s+(?:2026|2027)\b", "2026/2027 graduation target in JD"),
            (r"\b(?:2026|2027)\s+(?:batch|graduates?|pass[\s-]?outs?)\b", "2026/2027 batch in JD"),
            (r"\bgraduate\s+(?:hiring\s+)?program(?:me)?\b", "Graduate hiring program in JD"),
            (r"\bcampus\s+(?:hire|hiring|recruit|program)\b", "Campus hiring in JD"),
        ]
        for pat, label in strong_fresher_desc:
            if re.search(pat, fresher_check_desc):
                positive_signals.append(label)

        # IMPORTANT RULE from user:
        # "Do not assume a job is for freshers merely because its title says Associate, Graduate or Engineer.
        # Read the job description. If the job's fresher eligibility cannot be established, do not include it in my email."
        if not positive_signals:
            return False, "Fresher eligibility not established in title or job description", []

        # Extra strictness: If the ONLY positive signal is a generic title like "Graduate Engineer" without a readable JD
        # (unless it's explicitly Intern / New Grad / University Graduate / Fresher / Entry Level in title), require JD text!
        unambiguous_title = is_intern_title or bool(re.search(
            r"\b(?:fresher|new\s+grad|university\s+grad|entry[\s-]?level|campus|trainee|apprentice)\b",
            title_clean
        ))
        if not unambiguous_title and len(desc_clean) < 60:
            return False, "Job description missing/too short to confirm fresher eligibility", []

        return True, f"Confirmed fresher-eligible ({'; '.join(positive_signals[:3])})", positive_signals

    def evaluate(self, title: str, location: str, description: str) -> FilterDecision:
        """
        Runs all strict filters in order:
        1. Role relevance & Seniority exclusion
        2. India location filter
        3. B.Tech Electrical Engineering degree & branch filter
        4. 2027 Graduation year filter
        5. Strict fresher experience verification
        """
        role_ok, role_reason = self.check_role(title)
        if not role_ok:
            return FilterDecision(False, role_reason)

        loc_ok, loc_reason = self.check_location(location, title, description)
        if not loc_ok:
            return FilterDecision(False, loc_reason)

        deg_ok, deg_reason = self.check_degree_and_branch(description)
        if not deg_ok:
            return FilterDecision(False, deg_reason)

        grad_ok, grad_reason = self.check_graduation_year(title, description)
        if not grad_ok:
            return FilterDecision(False, grad_reason)

        exp_ok, exp_reason, signals = self.check_fresher_experience(title, description)
        if not exp_ok:
            return FilterDecision(False, exp_reason)

        return FilterDecision(True, exp_reason, signals)
