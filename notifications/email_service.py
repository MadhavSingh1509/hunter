"""
Hunter — Minimal 4-Field Email Notification Service
Sends ONLY four fields per confirmed fresher opportunity:
Company | Position Name | Posted On | Apply Link

Subject: Hunter — New Fresher Job Opportunities
No match scores, no salaries, no descriptions, no stats, no dashboards.
"""

import os
import html
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import List, Dict, Any, Tuple


SIMPLE_EMAIL_SUBJECT = "Hunter — New Fresher Job Opportunities"


class HunterEmailService:
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 465):
        self.smtp_server = os.environ.get("SMTP_SERVER", smtp_server).strip() or smtp_server
        self.smtp_port = int(os.environ.get("SMTP_PORT", str(smtp_port)).strip() or smtp_port)
        self.email_user = (os.environ.get("EMAIL_USER") or os.environ.get("EMAIL_ADDRESS") or "").strip()
        self.email_pass = (os.environ.get("EMAIL_PASS") or os.environ.get("EMAIL_PASSWORD") or "").strip()
        self.email_to = (os.environ.get("EMAIL_TO") or self.email_user or "adityamadhav1509@gmail.com").strip()

    def is_configured(self) -> bool:
        return bool(self.email_user and self.email_pass)

    @staticmethod
    def build_simple_digest(jobs: List[Dict[str, Any]]) -> Tuple[str, str, str]:
        """
        Builds the exact 4-field minimal email digest:
        Company | Position Name | Posted On | Apply Link
        Returns (subject, plain_text, html_body).
        """
        subject = SIMPLE_EMAIL_SUBJECT

        # Plain-text version: exact 4 fields per row
        plain_lines = ["Company | Position Name | Posted On | Apply Link"]
        html_rows = []

        for job in jobs:
            company = str(job.get("company_name") or job.get("company") or "").strip()
            title = str(job.get("title") or job.get("position") or "").strip()
            posted_on = str(job.get("posted_on") or "Not disclosed").strip() or "Not disclosed"
            apply_url = str(job.get("canonical_url") or job.get("apply_url") or job.get("url") or "").strip()

            plain_lines.append(f"{company} | {title} | {posted_on} | {apply_url}")

            c_esc = html.escape(company)
            t_esc = html.escape(title)
            p_esc = html.escape(posted_on)
            u_esc = html.escape(apply_url, quote=True)

            html_rows.append(
                f"<tr>"
                f"<td style=\"padding:10px 12px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#0f172a;\">{c_esc}</td>"
                f"<td style=\"padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#1e293b;\">{t_esc}</td>"
                f"<td style=\"padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#475569;white-space:nowrap;\">{p_esc}</td>"
                f"<td style=\"padding:10px 12px;border-bottom:1px solid #e2e8f0;white-space:nowrap;\">"
                f"<a href=\"{u_esc}\" target=\"_blank\" style=\"color:#2563eb;font-weight:600;text-decoration:none;\">Apply Link</a>"
                f"</td>"
                f"</tr>"
            )

        plain_text = "\n".join(plain_lines)
        rows_html = "\n".join(html_rows)

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;margin:0;padding:16px;background:#ffffff;color:#0f172a;">
<table cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:800px;border-collapse:collapse;font-size:14px;">
  <thead>
    <tr style="background:#f8fafc;border-bottom:2px solid #cbd5e1;text-align:left;">
      <th style="padding:10px 12px;color:#334155;">Company</th>
      <th style="padding:10px 12px;color:#334155;">Position Name</th>
      <th style="padding:10px 12px;color:#334155;">Posted On</th>
      <th style="padding:10px 12px;color:#334155;">Apply Link</th>
    </tr>
  </thead>
  <tbody>
{rows_html}
  </tbody>
</table>
</body>
</html>"""

        return subject, plain_text, html_body

    def send_simple_digest(self, jobs: List[Dict[str, Any]]) -> bool:
        """Sends the minimal 4-field email ONLY when there is at least 1 confirmed fresher job."""
        if not jobs:
            print("[EmailService] 0 new confirmed fresher openings. Skipping email.")
            return False

        if not self.is_configured():
            print("[EmailService] EMAIL_USER or EMAIL_PASS not configured. Skipping SMTP dispatch.")
            return False

        subject, plain_text, html_body = self.build_simple_digest(jobs)

        recipients = [r.strip() for r in self.email_to.split(",") if r.strip()]
        if "adityamadhav1509@gmail.com" not in recipients:
            recipients.append("adityamadhav1509@gmail.com")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_user
        msg["To"] = ", ".join(recipients)
        msg["Reply-To"] = self.email_user
        msg["Return-Path"] = self.email_user
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="gmail.com" if "gmail.com" in self.email_user.lower() else None)

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        sender_domain = self.email_user.split("@")[-1] if "@" in self.email_user else "unknown"
        sender_masked = f"{self.email_user[:3]}***@{sender_domain}" if len(self.email_user) > 3 else self.email_user
        recipients_masked = [f"{r[:3]}***@{r.split('@')[-1]}" for r in recipients]

        try:
            print(f"[EmailService] Connecting to {self.smtp_server}:{self.smtp_port} as {sender_masked}...")
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=20) as server:
                server.login(self.email_user, self.email_pass)
                refused = server.sendmail(self.email_user, recipients, msg.as_string())
                if refused:
                    print(f"[EmailService] Warning: Some recipients were refused: {refused}")
                else:
                    print(f"[EmailService] Delivered {len(jobs)} fresher openings to {', '.join(recipients_masked)} (250 OK).")
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send email via SMTP: {e}")
            return False
