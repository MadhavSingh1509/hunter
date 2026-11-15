"""
Hunter 2.0 Email Alert System
Builds and sends responsive HTML email digests for verified job opportunities.
Adheres strictly to the user's requested layout, match scores, explanations, and direct apply buttons.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Tuple, Optional
from qualification_engine import QualificationResult


def build_email_digest(
    verified_matches: List[QualificationResult],
    potential_matches: Optional[List[QualificationResult]] = None
) -> Tuple[str, str, str]:
    """
    Constructs the Subject, Plain-text body, and HTML body for the digest.
    Returns: (subject, plain_text, html_body)
    """
    potential_matches = potential_matches or []
    count = len(verified_matches)

    if count == 0:
        subject = "HUNTER | 0 Verified Job Opportunities Worth Applying For"
        plain_text = (
            "No verified matching opportunities found in this scan. "
            "Hunter will continue monitoring career portals every 12 hours."
        )
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; background-color:#f8fafc; padding:24px; color:#1e293b;">
          <div style="max-width:620px; margin:0 auto; background:#ffffff; border-radius:12px; padding:32px; border:1px solid #e2e8f0; text-align:center;">
            <div style="font-size:24px; font-weight:bold; color:#0f172a; margin-bottom:8px;">HUNTER 2.0</div>
            <div style="font-size:14px; color:#64748b; margin-bottom:24px;">Automated Career Portal Monitoring</div>
            <div style="padding:20px; background:#f1f5f9; border-radius:8px; font-size:15px; color:#334155; line-height:1.6;">
              <strong>No verified matching opportunities found in this scan.</strong><br>
              Hunter evaluated active openings across company career pages and filtered out irrelevant roles, strict experience gates, and closed listings.<br><br>
              Hunter will continue monitoring and notify you as soon as eligible positions appear.
            </div>
          </div>
        </body>
        </html>
        """
        return subject, plain_text, html_body

    subject = f"HUNTER | {count} Verified Job {'Opportunity' if count == 1 else 'Opportunities'} Worth Applying For"

    # Plain text version
    pt_lines = [
        f"HUNTER 2.0 — {count} Verified Job Opportunities Worth Applying For\n",
        "The following opportunities satisfy all mandatory eligibility criteria, have been verified active, and provide direct application links.\n",
        "=" * 60
    ]

    html_cards = []

    for res in verified_matches:
        job = res.job
        exp_data = res.details.get("experience", {})
        edu_data = res.details.get("education", {})
        grad_data = res.details.get("grad_year", {})
        matched_skills = res.details.get("matched_skills", [])

        # Format details
        exp_text = "0–1 years (Fresher eligible)" if exp_data.get("is_freshers_explicit") else "0-1 years"
        if exp_data.get("is_borderline"):
            exp_text = "0-2 years (Borderline)"

        degree_text = "B.Tech/B.E. in any engineering branch (Electrical Engineering eligible)"
        if edu_data.get("branch_status") == "EXPLICIT_EE":
            degree_text = "B.Tech/B.E. — Electrical Engineering explicitly accepted"

        batches = grad_data.get("disclosed_batches", [])
        grad_text = ", ".join(map(str, batches)) if batches else "Not Disclosed (Open to all entry-level)"

        skills_text = ", ".join(matched_skills[:6]) if matched_skills else "General Problem Solving, Programming"
        posted_date = job.posted_date or "Recently posted"

        # Highlights
        highlights = res.match_highlights
        if not highlights:
            highlights = [
                "Freshers explicitly accepted",
                "Electrical Engineering graduates eligible",
                "Application verified currently open",
                "Direct official application portal"
            ]

        # Plain text card
        pt_lines.append(f"\nCOMPANY: {job.company}")
        pt_lines.append(f"POSITION: {job.title}")
        pt_lines.append(f"LOCATION: {job.location or 'India'}")
        pt_lines.append(f"JOB TYPE: {job.job_type}")
        pt_lines.append(f"EXPERIENCE: {exp_text}")
        pt_lines.append(f"ELIGIBILITY: {degree_text}")
        pt_lines.append(f"GRADUATION BATCH: {grad_text}")
        pt_lines.append(f"SKILLS: {skills_text}")
        pt_lines.append(f"POSTED DATE: {posted_date}")
        pt_lines.append(f"JOB ID: {job.job_id}")
        pt_lines.append(f"MATCH SCORE: {res.score}/100")
        pt_lines.append("WHY THIS MATCHES:")
        for h in highlights:
            pt_lines.append(f"  - {h}")
        pt_lines.append(f"APPLY DIRECTLY: {job.url}\n")
        pt_lines.append("-" * 60)

        # HTML Card
        hl_items = "".join(f"<li style='margin-bottom:4px; color:#334155;'>{h}</li>" for h in highlights)

        card_html = f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:24px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
              <span style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#2563eb; background:#eff6ff; padding:4px 8px; border-radius:4px;">{res.tier}</span>
              <h2 style="margin:8px 0 4px 0; font-size:19px; font-weight:700; color:#0f172a;">{job.title}</h2>
              <div style="font-size:15px; font-weight:600; color:#475569;">{job.company}</div>
            </div>
            <div style="text-align:right;">
              <div style="background:#10b981; color:#ffffff; font-weight:bold; font-size:15px; padding:6px 12px; border-radius:8px; display:inline-block;">
                {res.score}/100
              </div>
              <div style="font-size:11px; color:#64748b; margin-top:4px;">Match Score</div>
            </div>
          </div>

          <table style="width:100%; font-size:13px; color:#334155; margin-bottom:16px; border-collapse:collapse;">
            <tr><td style="padding:4px 0; width:140px; color:#64748b; font-weight:600;">Location</td><td>{job.location or 'India'}</td></tr>
            <tr><td style="padding:4px 0; color:#64748b; font-weight:600;">Job Type</td><td>{job.job_type}</td></tr>
            <tr><td style="padding:4px 0; color:#64748b; font-weight:600;">Experience</td><td><strong>{exp_text}</strong></td></tr>
            <tr><td style="padding:4px 0; color:#64748b; font-weight:600;">Eligibility</td><td>{degree_text}</td></tr>
            <tr><td style="padding:4px 0; color:#64748b; font-weight:600;">Graduation Batch</td><td>{grad_text}</td></tr>
            <tr><td style="padding:4px 0; color:#64748b; font-weight:600;">Key Skills</td><td>{skills_text}</td></tr>
            <tr><td style="padding:4px 0; color:#64748b; font-weight:600;">Posted Date</td><td>{posted_date}</td></tr>
            <tr><td style="padding:4px 0; color:#64748b; font-weight:600;">Job ID</td><td><code>{job.job_id}</code></td></tr>
          </table>

          <div style="background:#f8fafc; border-left:4px solid #10b981; padding:12px 16px; border-radius:0 8px 8px 0; margin-bottom:18px;">
            <div style="font-size:13px; font-weight:bold; color:#0f172a; margin-bottom:6px;">WHY THIS MATCHES:</div>
            <ul style="margin:0; padding-left:18px; font-size:13px; line-height:1.5;">
              {hl_items}
            </ul>
          </div>

          <div>
            <a href="{job.url}" target="_blank" style="display:inline-block; background:#2563eb; color:#ffffff; padding:10px 22px; font-size:14px; font-weight:bold; text-decoration:none; border-radius:6px; box-shadow:0 1px 2px rgba(37,99,235,0.2);">
              APPLY DIRECTLY &rarr;
            </a>
          </div>
        </div>
        """
        html_cards.append(card_html)

    # Potential matches section
    potential_section_html = ""
    if potential_matches:
        pt_lines.append("\nPOTENTIAL OPPORTUNITIES (Requires quick manual review):\n")
        pot_cards = []
        for pres in potential_matches[:5]:
            pjob = pres.job
            pt_lines.append(f"- {pjob.company} | {pjob.title} (Score: {pres.score}/100)")
            pt_lines.append(f"  Link: {pjob.url}")
            for u in pres.uncertain_flags:
                pt_lines.append(f"  Note: {u}")
            pot_cards.append(f"""
            <div style="padding:10px 14px; border:1px solid #cbd5e1; border-radius:6px; margin-bottom:8px; font-size:13px;">
              <strong>{pjob.company}</strong> — <a href="{pjob.url}" style="color:#2563eb; text-decoration:none;">{pjob.title}</a> (Score: {pres.score}/100)<br>
              <span style="color:#b45309; font-size:12px;">{'; '.join(pres.uncertain_flags)}</span>
            </div>
            """)
        potential_section_html = f"""
        <div style="margin-top:28px; padding-top:20px; border-top:1px dashed #cbd5e1;">
          <h3 style="font-size:16px; color:#475569; margin-bottom:10px;">Potential Opportunities (Review Needed)</h3>
          {''.join(pot_cards)}
        </div>
        """

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; background-color:#f1f5f9; padding:24px; color:#1e293b; margin:0;">
      <div style="max-width:640px; margin:0 auto;">
        <div style="background:#0f172a; color:#ffffff; padding:24px; border-radius:12px 12px 0 0; text-align:center;">
          <h1 style="margin:0; font-size:22px; font-weight:800; letter-spacing:0.02em;">HUNTER 2.0</h1>
          <p style="margin:6px 0 0 0; font-size:14px; color:#94a3b8;">
            {count} Verified Opportunities Filtered for Your Profile
          </p>
        </div>
        <div style="background:#ffffff; padding:24px; border-radius:0 0 12px 12px; border:1px solid #e2e8f0; border-top:none;">
          <p style="font-size:14px; color:#475569; line-height:1.6; margin-top:0; margin-bottom:20px;">
            Hi Madhav, here are the latest opportunities that satisfied all mandatory qualification checks (B.Tech EE eligible, 0-1 years fresher experience, active official application link).
          </p>
          {''.join(html_cards)}
          {potential_section_html}
          <div style="text-align:center; font-size:12px; color:#94a3b8; margin-top:28px;">
            Hunter Job Monitor • Verified ATS Integration • Run schedule: Every 12 Hours
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    return subject, "\n".join(pt_lines), full_html


def send_email_digest(subject: str, plain_text: str, html_body: str) -> bool:
    """
    Delivers email alert via SMTP credentials from environment variables.
    """
    user = os.environ.get("EMAIL_ADDRESS")
    password = os.environ.get("EMAIL_PASSWORD")

    if not user or not password:
        print("[EMAIL] Skipping email dispatch: EMAIL_ADDRESS or EMAIL_PASSWORD not set in environment.")
        return False

    host = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    to_addr = os.environ.get("EMAIL_TO", user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(host, port, timeout=20) as server:
            server.login(user, password)
            server.sendmail(user, [to_addr], msg.as_string())
        print(f"[EMAIL] Alert successfully delivered to {to_addr}: '{subject}'")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email alert: {e}")
        return False
