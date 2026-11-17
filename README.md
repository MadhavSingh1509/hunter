# HUNTER 4.0 — Automated India Fresher SDE & AI/ML Job Discovery System

**Hunter 4.0** is an automated, production-grade job discovery, verification, and notification system designed to find genuine, currently open fresher software engineering and AI/ML opportunities across 167 top employers in India.

---

## 🎯 Candidate Profile & Targeting

Configured in `config/candidate_profile.json`:
- **Candidate:** Madhav Singh
- **Degree:** B.Tech in Electrical Engineering (EE)
- **Graduation Batch:** 2026 (Configurable)
- **Experience Level:** Fresher (0 years full-time software industry employment)
- **Target Compensation:** $\ge 12$ LPA (Undisclosed accepted; below 12 LPA classified separately)
- **Location:** India (Bengaluru, Hyderabad, Pune, Chennai, Mumbai, Delhi NCR, Noida, Gurgaon, Kolkata, Ahmedabad, Jaipur, Patna, etc.)
- **Roles:** Software Development Engineer (SDE I), Graduate Engineer, Backend/Frontend/Full-Stack, AI/ML Engineer, GenAI/LLM, Computer Vision, Internships

---

## 🏛️ Centralized Registries

1. **Company Registry (`config/company_registry.json`):**
   - **167 Employers** across 7 major sectors:
     - Section A: Global Big Tech (Microsoft, Amazon, AWS, Google, Adobe, Apple, NVIDIA, Uber, Walmart, Salesforce, etc.)
     - Section B: Banking, Finance & FinTech (Goldman Sachs, JPMorgan Chase, Morgan Stanley, Barclays, Amex, Visa, Stripe, DE Shaw, etc.)
     - Section C: Indian Product & Unicorns (Flipkart, Swiggy, Zomato, CRED, Razorpay, Freshworks, Postman, Groww, Meesho, etc.)
     - Section D: Enterprise SaaS & DevTools (Hasura, Zeta, Druva, Whatfix, Harness, Composio, TrueFoundry, Nanonets, etc.)
     - Section E: AI, GenAI & Deep-Tech (Sarvam AI, Krutrim, Neysa, Qure.ai, Pixxel, Skyroot, Fractal, etc.)
     - Section F: Semiconductor & Hardware (Synopsys, Cadence, Texas Instruments, Micron, AMD, Intel, Samsung R&D)
     - Section G: Additional Campus & Tech Recruiters (Accenture, Deloitte, EY, PwC, Publicis Sapient, TCS Research, etc.)
   - **Mandatory Priority Integrations:** **Amazon, Salesforce, Barclays, Accenture**.

2. **Campus Recruiter Watchlist (`config/campus_recruiter_registry.json`):**
   - **57 Campus Recruiters** with recorded recruitment history at IITs & NITs (including NIT Patna).
   - Priority A (27 companies) & Priority B (30 companies) with recurrence tracking (`RECURRING`, `OCCASIONAL`, `UNVERIFIED`).

---

## ⚙️ 7-Dimension Eligibility & Scoring Architecture

Every discovered opportunity is evaluated across 7 independent dimensions with hard rejection gates:
1. **Role Relevance (25 pts):** SDE and AI/ML positions. Hard rejection of Senior, Management, HR, and core electrical wiring/substation roles.
2. **Degree Eligibility (20 pts):** Evaluates non-CS background. Accepts "any engineering branch", "circuit branches", or explicit Electrical Engineering. Rejects "CSE/IT only" and mandatory Master's/Ph.D.
3. **Graduation Eligibility (15 pts):** Matches 2026 batch / final-year students. Rejects prior batches (2022/2023) or junior-year restrictions.
4. **Experience Eligibility (15 pts):** Accepts 0-1 years, freshers, interns. Rejects mandatory $\ge 2$ years full-time professional experience.
5. **Location Eligibility (10 pts):** Requires India location or India-eligible remote. Rejects non-India positions.
6. **Skills Alignment (10 pts):** Matches C++, Java, Python, JavaScript, React, Node.js, Express, MongoDB, SQL, DSA, REST APIs.
7. **Employment Type Preference (5 pts):** Full-time, Internship, PPO.

---

## 📬 4-Section Email Digest

Responsive HTML digest delivered via SMTP SSL:
- **Section 1: VERIFIED MATCHES** — Confirmed fresher, EE eligible, open in India.
- **Section 2: POTENTIAL MATCHES** — Technical opportunities with review notes highlighting unstated details.
- **Section 3: BELOW-TARGET COMPENSATION** — Relevant opportunities $< 12$ LPA displayed separately.
- **Section 4: NEW & UPDATED OPPORTUNITIES** — Newly discovered jobs and status upgrades.
- **Zero Empty Emails:** Never sends misleading "0 openings" alerts when potential matches exist.

---

## 📊 Source Health & Diagnostics

Tracks real-time health across every company scanner:
- `HEALTHY`: Endpoint responsive, jobs parsed successfully.
- `DEGRADED`: Partial response or required fallbacks.
- `FAILED`: Endpoint returned HTTP error or timeout.
- `NOT_CONFIGURED`: Company in watchlist awaiting direct endpoint adapter.

---

## 🚀 Running Hunter 4.0 Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run automated test suite (57 tests)
pytest -v

# 3. Run Hunter 4.0 Discovery & Verification
python monitor.py
```
