"""
Hunter 4.0 - Source Health and Diagnostics Engine
Tracks health status (HEALTHY, DEGRADED, FAILED, NOT_CONFIGURED) across all 167 companies.
Generates structured diagnostic tables for console, email, and reports.
"""

from typing import List, Dict, Any, Optional

class SourceHealthMonitor:
    def __init__(self, db):
        self.db = db

    def generate_health_report(self) -> Dict[str, Any]:
        """
        Queries source health summary from the database and returns
        aggregate metrics and formatted tables.
        """
        records = self.db.get_source_health_summary()
        
        healthy = [r for r in records if r["health_status"] == "HEALTHY"]
        degraded = [r for r in records if r["health_status"] == "DEGRADED"]
        failed = [r for r in records if r["health_status"] == "FAILED"]
        not_configured = [r for r in records if r["health_status"] == "NOT_CONFIGURED"]
        unknown = [r for r in records if r["health_status"] == "UNKNOWN"]

        total_jobs_retrieved = sum(r.get("jobs_retrieved", 0) for r in records)
        total_relevant = sum(r.get("relevant_jobs_found", 0) for r in records)
        total_verified = sum(r.get("verified_matches", 0) for r in records)
        total_potential = sum(r.get("potential_matches", 0) for r in records)

        return {
            "total_companies": len(records),
            "healthy_count": len(healthy),
            "degraded_count": len(degraded),
            "failed_count": len(failed),
            "not_configured_count": len(not_configured),
            "unknown_count": len(unknown),
            "total_jobs_retrieved": total_jobs_retrieved,
            "total_relevant_found": total_relevant,
            "total_verified_matches": total_verified,
            "total_potential_matches": total_potential,
            "records": records
        }

    def format_markdown_table(self, limit_not_configured: bool = True) -> str:
        """Formats a clean GitHub Markdown diagnostic table."""
        report = self.generate_health_report()
        records = report["records"]

        lines = [
            "### Source Health & Diagnostics Report",
            "",
            f"**Total Registered Companies:** {report['total_companies']} | **Active/Healthy:** {report['healthy_count']} | **Degraded:** {report['degraded_count']} | **Failed:** {report['failed_count']} | **Not Yet Configured:** {report['not_configured_count']}",
            f"**Total Jobs Retrieved:** {report['total_jobs_retrieved']} | **Relevant Jobs:** {report['total_relevant_found']} | **Verified Matches:** {report['total_verified_matches']} | **Potential Matches:** {report['total_potential_matches']}",
            "",
            "| Company | Status | Scanner / ATS | Jobs Retrieved | Relevant | Verified | Potential | Last Checked |",
            "|:---|:---:|:---|---:|---:|---:|---:|:---|"
        ]

        # Prioritize mandatory companies and active/scanned companies
        for r in records:
            status = r["health_status"]
            if limit_not_configured and status == "NOT_CONFIGURED" and not r.get("is_mandatory_priority"):
                continue

            badge = {
                "HEALTHY": "🟢 HEALTHY",
                "DEGRADED": "🟡 DEGRADED",
                "FAILED": "🔴 FAILED",
                "NOT_CONFIGURED": "⚪ NOT_CONFIGURED",
                "UNKNOWN": "⚪ UNCHECKED"
            }.get(status, status)

            name = f"**{r['name']}**" if r.get("is_mandatory_priority") else r["name"]
            ats = r.get("ats_type", "custom")
            retrieved = r.get("jobs_retrieved", 0)
            rel = r.get("relevant_jobs_found", 0)
            ver = r.get("verified_matches", 0)
            pot = r.get("potential_matches", 0)
            last = str(r.get("last_attempted_at") or "-")[:10]

            lines.append(f"| {name} | {badge} | {ats} | {retrieved} | {rel} | {ver} | {pot} | {last} |")

        if limit_not_configured and report["not_configured_count"] > 0:
            lines.append(f"\n*(+ {report['not_configured_count']} additional companies registered in watchlist awaiting direct endpoint integrations)*")

        return "\n".join(lines)
