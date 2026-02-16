#!/usr/bin/env python3
"""CLI for the WebSoc scraper. Run as: python -m src.websoc.cli (or python -m websoc.cli)."""
import argparse
import json
import sys
from pathlib import Path

from .scraper import fetch_class_sessions
from .terms import get_current_term


def main():
    parser = argparse.ArgumentParser(description="UCI WebSoc scraper — output class sessions as JSON")
    parser.add_argument("--term", help='e.g. "2025 Fall"')
    parser.add_argument("--current", action="store_true", help="use current quarter")
    parser.add_argument("--dept", dest="department", help="department code, e.g. I&C SCI")
    parser.add_argument("--ge", help="GE code, e.g. GE-2")
    parser.add_argument("--instructor", dest="instructorName", help="instructor last name")
    parser.add_argument("--course", dest="courseNumber", help="course number or range")
    parser.add_argument("--limit", type=int, help="max sessions to output")
    parser.add_argument("--output", "-o", help="write JSON to file")
    args = parser.parse_args()

    opts = {}
    if args.current:
        opts["term"] = get_current_term()
    elif args.term:
        opts["term"] = args.term
    else:
        print("Usage: python -m src.websoc.cli --term \"2025 Fall\" --dept \"I&C SCI\" [--limit N]", file=sys.stderr)
        print("       python -m src.websoc.cli --current --dept \"I&C SCI\"   (current quarter)", file=sys.stderr)
        sys.exit(1)

    if args.department:
        opts["department"] = args.department
    if args.ge:
        opts["ge"] = args.ge
    if args.instructorName:
        opts["instructorName"] = args.instructorName
    if args.courseNumber:
        opts["courseNumber"] = args.courseNumber

    if not any(opts.get(k) for k in ("department", "ge", "instructorName")):
        print("Provide at least one of: --dept, --ge, --instructor", file=sys.stderr)
        sys.exit(1)

    try:
        sessions = fetch_class_sessions(opts)
    except Exception as e:
        print(f"Scraper error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.limit and args.limit > 0:
        sessions = sessions[: args.limit]

    json_str = json.dumps(sessions, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_str, encoding="utf-8")
        print(f"Wrote {len(sessions)} session(s) to {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
