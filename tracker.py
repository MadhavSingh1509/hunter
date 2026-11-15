"""
Hunter 2.0 CLI Application Tracker
Usage:
  python tracker.py list [optional_status_filter]
  python tracker.py apply <job_id> [optional_notes]
  python tracker.py status <job_id> <status> [optional_notes]
  python tracker.py add <company> <title> <url> [match_score]
  python tracker.py export [optional_output_path]
"""

import sys
from application_tracker import ApplicationTracker, VALID_STATUSES


def print_table(rows):
    if not rows:
        print("No job applications found.")
        return

    # Print summary cards
    print("\n" + "=" * 90)
    print(f"{'STATUS':<20} | {'COMPANY':<20} | {'JOB TITLE':<30} | {'SCORE':<5}")
    print("=" * 90)
    for r in rows:
        status = r.get("status", "Interested")
        company = r.get("company", "")[:18]
        title = r.get("title", "")[:28]
        score = str(r.get("match_score", "-"))
        print(f"{status:<20} | {company:<20} | {title:<30} | {score:<5}")
        if r.get("url"):
            print(f"  URL: {r['url']}")
        if r.get("notes"):
            print(f"  Notes: {r['notes']}")
        if r.get("date_applied"):
            print(f"  Applied on: {r['date_applied']}")
        print("-" * 90)


def main():
    tracker = ApplicationTracker()
    args = sys.argv[1:]

    if not args or args[0] in ["list", "ls"]:
        status_filter = args[1] if len(args) > 1 else None
        rows = tracker.list_applications(status_filter)
        print_table(rows)
        print(f"\nTotal tracked jobs: {len(rows)}")
        print(f"CSV exported to: {tracker.csv_file}")

    elif args[0] in ["apply", "applied"]:
        if len(args) < 2:
            print("Usage: python tracker.py apply <job_id> [optional_notes]")
            sys.exit(1)
        job_id = args[1]
        notes = " ".join(args[2:]) if len(args) > 2 else ""
        if tracker.update_status(job_id, "Applied", notes=notes):
            print(f"Successfully marked '{job_id}' as Applied!")
        else:
            print(f"Job ID '{job_id}' not found.")

    elif args[0] == "status":
        if len(args) < 3:
            print(f"Usage: python tracker.py status <job_id> <new_status>")
            print(f"Allowed statuses: {', '.join(VALID_STATUSES)}")
            sys.exit(1)
        job_id = args[1]
        status = args[2]
        notes = " ".join(args[3:]) if len(args) > 3 else None
        if tracker.update_status(job_id, status, notes=notes):
            print(f"Updated status of '{job_id}' to '{status}'.")
        else:
            print(f"Job ID '{job_id}' not found.")

    elif args[0] == "add":
        if len(args) < 4:
            print("Usage: python tracker.py add <company> <title> <url> [match_score] [job_id]")
            sys.exit(1)
        company = args[1]
        title = args[2]
        url = args[3]
        score = int(args[4]) if len(args) > 4 and args[4].isdigit() else 80
        import hashlib
        job_id = args[5] if len(args) > 5 else f"manual-{hashlib.sha1((company + title).encode()).hexdigest()[:8]}"
        tracker.record_job(job_id=job_id, company=company, title=title, url=url, match_score=score, status="Interested")
        print(f"Added '{title}' at '{company}' with Job ID '{job_id}' to tracker.")

    elif args[0] == "export":
        out_path = args[1] if len(args) > 1 else None
        tracker.export_csv(out_path)
        print(f"Applications exported successfully to {out_path or tracker.csv_file}.")

    else:
        print("Unknown command. Supported: list, apply, status, export")


if __name__ == "__main__":
    main()
