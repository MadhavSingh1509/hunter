"""
Hunter 4.0 - Email Notification Service & Responsive Digest Generator
Implements 4 mandatory sections:
1. VERIFIED MATCHES (Confirmed Fresher, EE Eligible, India, Open)
2. POTENTIAL MATCHES (Technical matches with unknown eligibility details clearly stated)
3. BELOW-TARGET COMPENSATION (Relevant matches < 12 LPA)
4. NEW AND UPDATED JOBS (State transitions & newly discovered opportunities)
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict, Any, Optional

class HunterEmailService:
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 465):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_user = os.environ.get("EMAIL_USER") or os.environ.get("EMAIL_ADDRESS") or ""
        self.email_pass = os.environ.get("EMAIL_PASS") or os.environ.get("EMAIL_PASSWORD") or ""
        self.email_to = os.environ.get("EMAIL_TO") or self.email_user or "adityamadhav1509@gmail.com"

    def is_configured(self) -> bool:
        return bool(self.email_user and self.email_pass)

    def generate_html_digest(self,
                             verified_matches: List[Dict[str, Any]],
                             potential_matches: List[Dict[str, Any]],
                             below_target_jobs: List[Dict[str, Any]],
                             new_updated_jobs: List[Dict[str, Any]],
                             scan_summary: Dict[str, Any]) -> str:
        """Generates a responsive, 4-section HTML digest."""
        now_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")
        total_opportunities = len(verified_matches) + len(potential_matches) + len(below_target_jobs)

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }}
  .container {{ max-width: 680px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
  .header {{ background: linear-gradient(135deg, #2563eb, #1d4ed8); padding: 28px 24px; text-align: left; border-bottom: 2px solid #3b82f6; }}
  .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }}
  .header p {{ margin: 6px 0 0; font-size: 14px; color: #bfdbfe; }}
  .summary-bar {{ background-color: #0f172a; padding: 16px 24px; display: flex; flex-wrap: wrap; gap: 12px; border-bottom: 1px solid #334155; }}
  .stat-badge {{ background-color: #1e293b; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; font-size: 13px; color: #94a3b8; }}
  .stat-badge b {{ color: #38bdf8; }}
  .content {{ padding: 24px; }}
  .section-title {{ font-size: 17px; font-weight: 700; margin: 28px 0 14px; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; }}
  .section-verified {{ color: #22c55e; border-bottom: 2px solid #22c55e; padding-bottom: 6px; }}
  .section-potential {{ color: #f59e0b; border-bottom: 2px solid #f59e0b; padding-bottom: 6px; }}
  .section-below {{ color: #94a3b8; border-bottom: 2px solid #64748b; padding-bottom: 6px; }}
  .section-updates {{ color: #38bdf8; border-bottom: 2px solid #38bdf8; padding-bottom: 6px; }}
  .job-card {{ background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 18px; margin-bottom: 16px; }}
  .job-card:hover {{ border-color: #3b82f6; }}
  .job-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }}
  .job-title {{ font-size: 16px; font-weight: 700; color: #ffffff; margin: 0; }}
  .company-name {{ font-size: 14px; font-weight: 600; color: #38bdf8; margin: 2px 0 6px; }}
  .score-badge {{ background-color: #1e3a8a; color: #93c5fd; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; }}
  .job-meta {{ font-size: 13px; color: #94a3b8; margin-bottom: 10px; line-height: 1.5; }}
  .job-meta span {{ margin-right: 14px; display: inline-block; }}
  .notes-box {{ background-color: #1e293b; border-left: 3px solid #f59e0b; padding: 8px 12px; font-size: 12px; color: #cbd5e1; margin-bottom: 12px; border-radius: 0 4px 4px 0; }}
  .apply-btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; text-align: center; }}
  .apply-btn:hover {{ background-color: #1d4ed8; }}
  .footer {{ padding: 20px 24px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #334155; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>HUNTER 4.0 &bull; Job Alert Digest</h1>
    <p>Automated Fresher SDE & AI/ML Opportunities &bull; {now_str}</p>
  </div>

  <div class="summary-bar">
    <div class="stat-badge">Scanned: <b>{scan_summary.get('companies_scanned', 0)} companies</b></div>
    <div class="stat-badge">Jobs Retrieved: <b>{scan_summary.get('jobs_retrieved', 0)}</b></div>
    <div class="stat-badge">Verified: <b style="color:#22c55e;">{len(verified_matches)}</b></div>
    <div class="stat-badge">Potential: <b style="color:#f59e0b;">{len(potential_matches)}</b></div>
  </div>

  <div class="content">
"""

        # Section 1: VERIFIED MATCHES
        if verified_matches:
            html += """<div class="section-title section-verified">🎯 SECTION 1: VERIFIED MATCHES (Confirmed Eligibility)</div>"""
            for j in verified_matches:
                html += f"""
                <div class="job-card">
                  <div class="job-header">
                    <div>
                      <h3 class="job-title">{j.get('title')}</h3>
                      <div class="company-name">{j.get('company_name')}</div>
                    </div>
                    <span class="score-badge" style="background-color:#14532d; color:#86efac;">Match Score: {j.get('match_score', 0):.1f}</span>
                  </div>
                  <div class="job-meta">
                    <span>📍 <b>Location:</b> {j.get('location', 'India')}</span>
                    <span>💼 <b>Type:</b> {j.get('employment_type', 'Full-time')}</span>
                    <span>💰 <b>CTC:</b> {j.get('compensation_text', 'Not disclosed')}</span>
                    <br>
                    <span>🎓 <b>Degree:</b> B.Tech Electrical Engineering Eligible</span>
                    <span>⏳ <b>Experience:</b> 0-1 Years / Fresher</span>
                  </div>
                  <div class="notes-box" style="border-left-color:#22c55e;">
                    <b>Eligibility:</b> {j.get('eligibility_notes', 'All fresher criteria verified')}
                  </div>
                  <a href="{j.get('canonical_url')}" class="apply-btn" target="_blank">Direct Apply Link &rarr;</a>
                </div>
                """

        # Section 2: POTENTIAL MATCHES
        if potential_matches:
            html += """<div class="section-title section-potential">🔍 SECTION 2: POTENTIAL MATCHES (Review Required)</div>"""
            for j in potential_matches:
                html += f"""
                <div class="job-card">
                  <div class="job-header">
                    <div>
                      <h3 class="job-title">{j.get('title')}</h3>
                      <div class="company-name">{j.get('company_name')}</div>
                    </div>
                    <span class="score-badge">Score: {j.get('match_score', 0):.1f}</span>
                  </div>
                  <div class="job-meta">
                    <span>📍 <b>Location:</b> {j.get('location', 'India')}</span>
                    <span>💼 <b>Type:</b> {j.get('employment_type', 'Full-time')}</span>
                    <span>💰 <b>Compensation:</b> {j.get('compensation_text', 'Not disclosed')}</span>
                  </div>
                  <div class="notes-box">
                    <b>Attention:</b> {j.get('eligibility_notes', 'Review full description for branch/batch requirements')}
                  </div>
                  <a href="{j.get('canonical_url')}" class="apply-btn" style="background-color:#d97706;" target="_blank">Review & Apply &rarr;</a>
                </div>
                """

        # Section 3: BELOW-TARGET COMPENSATION
        if below_target_jobs:
            html += """<div class="section-title section-below">📋 SECTION 3: BELOW ₹12 LPA MATCHES</div>"""
            for j in below_target_jobs:
                html += f"""
                <div class="job-card" style="opacity: 0.85;">
                  <div class="job-header">
                    <div>
                      <h3 class="job-title">{j.get('title')}</h3>
                      <div class="company-name">{j.get('company_name')}</div>
                    </div>
                    <span class="score-badge">Score: {j.get('match_score', 0):.1f}</span>
                  </div>
                  <div class="job-meta">
                    <span>📍 <b>Location:</b> {j.get('location', 'India')}</span>
                    <span>💰 <b>Disclosed CTC:</b> {j.get('compensation_text')}</span>
                  </div>
                  <a href="{j.get('canonical_url')}" class="apply-btn" style="background-color:#475569;" target="_blank">View Opportunity &rarr;</a>
                </div>
                """

        # Section 4: NEW AND UPDATED JOBS
        if new_updated_jobs:
            html += """<div class="section-title section-updates">⚡ SECTION 4: NEW & UPDATED STATUS OPPORTUNITIES</div>"""
            for j in new_updated_jobs:
                transition = j.get("transition_type", "NEW")
                html += f"""
                <div class="job-card">
                  <div class="job-header">
                    <div>
                      <h3 class="job-title">{j.get('title')}</h3>
                      <div class="company-name">{j.get('company_name')}</div>
                    </div>
                    <span class="score-badge" style="background-color:#0369a1; color:#e0f2fe;">Status: {transition}</span>
                  </div>
                  <div class="job-meta">
                    <span>📍 {j.get('location', 'India')} &bull; Status changed to {j.get('classification')}</span>
                  </div>
                  <a href="{j.get('canonical_url')}" class="apply-btn" style="background-color:#0284c7;" target="_blank">Direct Link &rarr;</a>
                </div>
                """

        html += f"""
  </div>
  <div class="footer">
    Hunter 4.0 &bull; Automated India Fresher SDE & AI/ML Discovery System<br>
    Configured for B.Tech Electrical Engineering (2026 Batch, Fresher)
  </div>
</div>
</body>
</html>
"""
        return html

    def send_digest(self,
                    verified_matches: List[Dict[str, Any]],
                    potential_matches: List[Dict[str, Any]],
                    below_target_jobs: List[Dict[str, Any]],
                    new_updated_jobs: List[Dict[str, Any]],
                    scan_summary: Dict[str, Any]) -> bool:
        """Sends email digest only when actionable opportunities exist."""
        total_jobs = len(verified_matches) + len(potential_matches) + len(below_target_jobs) + len(new_updated_jobs)
        
        # Mandatory guardrail: Do not send empty email or misleading zero alert
        if total_jobs == 0:
            print("[EmailService] No unnotified matches or updates to send. Skipping empty digest.")
            return False

        if not self.is_configured():
            print("[EmailService] EMAIL_USER or EMAIL_PASS not configured. Digest generated but not sent via SMTP.")
            return False

        html_content = self.generate_html_digest(
            verified_matches, potential_matches, below_target_jobs, new_updated_jobs, scan_summary
        )

        subject = f"🎯 Hunter 4.0: {len(verified_matches)} Verified | {len(potential_matches)} Potential Fresher SDE/AI Jobs"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Hunter 4.0 <{self.email_user}>"
        msg["To"] = self.email_to

        text_part = MIMEText(
            f"Hunter 4.0 Job Alert\nVerified: {len(verified_matches)}\nPotential: {len(potential_matches)}\nPlease view the HTML version for direct application links.",
            "plain"
        )
        html_part = MIMEText(html_content, "html")

        msg.attach(text_part)
        msg.attach(html_part)

        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.login(self.email_user, self.email_pass)
                server.sendmail(self.email_user, [self.email_to], msg.as_string())
            print(f"[EmailService] Successfully sent digest to {self.email_to} with {total_jobs} opportunities.")
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send email via SMTP: {e}")
            return False
