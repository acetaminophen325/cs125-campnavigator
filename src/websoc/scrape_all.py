#!/usr/bin/env python3
"""Scrape all departments for current quarter. Run as: python -m src.websoc.scrape_all (or python -m websoc.scrape_all)."""
import json
import sys
import time
from pathlib import Path

from .anteater import fetch_departments_for_term
from .scraper import fetch_class_sessions
from .terms import get_current_term, get_current_term_for_anteater

DELAY_SEC = 0.4


def main():
    args = sys.argv[1:]
    output = "data/sessions.json"
    for i, a in enumerate(args):
        if a == "--output" and i + 1 < len(args):
            output = args[i + 1]
            break

    term = get_current_term()
    for_anteater = get_current_term_for_anteater()
    if not for_anteater:
        print(f"Could not parse current term: {term}", file=sys.stderr)
        sys.exit(1)

    print(f"Term: {term}", file=sys.stderr)
    print("Fetching department list...", file=sys.stderr)
    try:
        departments = fetch_departments_for_term(for_anteater["year"], for_anteater["quarter"])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(departments)} departments.", file=sys.stderr)
    all_sessions = []

    for i, dept in enumerate(departments):
        dept_code = dept.get("deptCode", "")
        dept_name = dept.get("deptName", "")
        print(f"  [{i + 1}/{len(departments)}] {dept_code} ({dept_name})... ", end="", file=sys.stderr)
        try:
            sessions = fetch_class_sessions({"term": term, "department": dept_code})
            for s in sessions:
                s["departmentName"] = dept_name
            all_sessions.extend(sessions)
            print(f"{len(sessions)} session(s)", file=sys.stderr)
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
        if i < len(departments) - 1:
            time.sleep(DELAY_SEC)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(all_sessions, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_sessions)} session(s) to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
