# scripts/parse_websoc_json.py
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


OUT_COLUMNS = [
    "meeting_id",
    "course_id",
    "title",
    "dept",
    "days",
    "start_min",
    "end_min",
    "building_code",
    "room",
    "term",
]


DAY_MAP = {
    # common encodings
    "M": "M",
    "T": "Tu",   # some feeds use T for Tue
    "Tu": "Tu",
    "W": "W",
    "Th": "Th",
    "R": "Th",   # some feeds use R for Thu
    "F": "F",
    "Sa": "Sa",
    "Su": "Su",
}


def normalize_days(days_raw: str) -> str:
    """
    Converts day encodings into a compact string like 'MWF' or 'TuTh'.
    Input examples: 'W', 'MWF', 'TuTh', 'TR', 'TTh'
    """
    if not days_raw:
        return ""

    s = days_raw.strip()

    # Handle compact encodings like "TR" meaning Tue/Thu
    # We'll interpret 'T' as Tue and 'R' as Thu
    if s == "TR":
        return "TuTh"
    if s == "TTh":
        return "TuTh"

    # If it already looks like TuTh or contains Th, keep as-is but normalize T->Tu if needed
    # We'll parse tokens in order.
    tokens: List[str] = []

    i = 0
    while i < len(s):
        # Prefer 2-char tokens first (Tu, Th, Sa, Su)
        if s[i : i + 2] in ("Tu", "Th", "Sa", "Su"):
            tokens.append(s[i : i + 2])
            i += 2
            continue

        ch = s[i]
        if ch in ("M", "W", "F"):
            tokens.append(ch)
        elif ch == "T":
            tokens.append("Tu")
        elif ch == "R":
            tokens.append("Th")
        i += 1

    # Deduplicate while preserving order
    seen = set()
    out = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)

    return "".join(out)


def parse_location(loc_raw: str) -> Tuple[str, str]:
    """
    Example: "HIB 411" -> ("HIB", "411")
             "SSLH 100" -> ("SSLH", "100")
             "ONLINE" / "TBA" -> ("", "")
    """
    if not loc_raw:
        return ("", "")
    s = loc_raw.strip()
    if s.upper() in {"TBA", "ONLINE", "REMOTE", "WEB", "ARR"}:
        return ("", "")

    parts = s.split()
    if len(parts) == 1:
        # Sometimes just the building code
        return (parts[0], "")
    building = parts[0]
    room = " ".join(parts[1:])
    return (building, room)


TIME_RANGE_RE = re.compile(
    r"""
    ^\s*
    (?P<start>\d{1,2}:\d{2})(?P<start_suffix>[ap]m?|[ap])?
    \s*[-–—]\s*
    (?P<end>\d{1,2}:\d{2})(?P<end_suffix>[ap]m?|[ap])?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def time_to_minutes(hhmm: str, ampm: str) -> int:
    """
    hhmm: '2:00'
    ampm: 'a'/'p'/'am'/'pm' (case-insensitive)
    Returns minutes since midnight (0..1439)
    """
    h_str, m_str = hhmm.split(":")
    h = int(h_str)
    m = int(m_str)

    a = ampm.lower()
    if a in ("a", "am"):
        if h == 12:
            h = 0
    elif a in ("p", "pm"):
        if h != 12:
            h += 12
    else:
        raise ValueError(f"Invalid am/pm suffix: {ampm}")

    return h * 60 + m


def infer_ampm_suffix(time_str: str) -> Optional[str]:
    """
    For strings like '2:00 - 4:50p' or '2:00-4:50pm', return 'p' or 'pm'.
    """
    m = TIME_RANGE_RE.match(time_str)
    if not m:
        return None
    suf = m.group("suffix")
    if not suf:
        return None
    return suf.lower()


def parse_meeting_time(time_raw: str) -> Optional[Tuple[int, int]]:
    """
    Parses meetingTime like:
      '2:00- 4:50p'
      '2:00 - 4:50pm'
    Assumption (based on your screenshot): AM/PM suffix is usually only given once at the end.
    We apply it to BOTH start and end.
    Returns (start_min, end_min) or None if unusable (TBA/empty).
    """
    if not time_raw:
        return None
    s = time_raw.strip()
    if not s or s.upper() == "TBA":
        return None

    # Try without spaces first, then with spaces
    m = TIME_RANGE_RE.match(s.replace(" ", ""))
    if not m:
        m = TIME_RANGE_RE.match(s)
    if not m:
        return None

    start_hhmm = m.group("start")
    end_hhmm = m.group("end")
    start_suf = m.group("start_suffix")
    end_suf = m.group("end_suffix")

    def norm_suf(x: Optional[str]) -> Optional[str]:
        if not x:
            return None
        a = x.lower()
        if a in ("a", "am"):
            return "am"
        if a in ("p", "pm"):
            return "pm"
        return None

    start_suf = norm_suf(start_suf)
    end_suf = norm_suf(end_suf)

    # Helper: choose between AM/PM for an unmarked time based on closeness
    def choose_closest(unmarked_hhmm: str, marked_min: int) -> Optional[Tuple[int, str]]:
        best = None
        for candidate in ("am", "pm"):
            try:
                mmin = time_to_minutes(unmarked_hhmm, candidate)
            except ValueError:
                continue
            delta = abs(mmin - marked_min)
            if best is None or delta < best[0]:
                best = (delta, mmin, candidate)
        if best is None:
            return None
        return (best[1], best[2])

    # Default heuristic mapping when no suffixes are present at all
    def default_ampm_for_hour(h: int) -> str:
        # Interpret 9-11 (and 8) as AM; 12 and 1-7 as PM. Fallback AM.
        if 8 <= h <= 11:
            return "am"
        if h == 12 or 1 <= h <= 7:
            return "pm"
        return "am"

    # Case 1: both suffixes present -> use them
    if start_suf and end_suf:
        try:
            start_min = time_to_minutes(start_hhmm, start_suf)
            end_min = time_to_minutes(end_hhmm, end_suf)
        except ValueError:
            return None
        if end_min <= start_min:
            return None
        return (start_min, end_min)

    # Case 2: one suffix present -> infer the other by closeness while keeping start < end
    if end_suf and not start_suf:
        try:
            end_min = time_to_minutes(end_hhmm, end_suf)
        except ValueError:
            return None
        choice = choose_closest(start_hhmm, end_min)
        if not choice:
            return None
        start_min, _suf = choice
        if start_min >= end_min:
            return None
        return (start_min, end_min)

    if start_suf and not end_suf:
        try:
            start_min = time_to_minutes(start_hhmm, start_suf)
        except ValueError:
            return None
        choice = choose_closest(end_hhmm, start_min)
        if not choice:
            return None
        end_min, _suf = choice
        if end_min <= start_min:
            return None
        return (start_min, end_min)

    # Case 3: no suffixes at all -> apply default hour-based mapping
    try:
        sh = int(start_hhmm.split(":")[0])
        eh = int(end_hhmm.split(":")[0])
    except Exception:
        return None

    s_amp = default_ampm_for_hour(sh)
    e_amp = default_ampm_for_hour(eh)
    try:
        start_min = time_to_minutes(start_hhmm, s_amp)
        end_min = time_to_minutes(end_hhmm, e_amp)
    except ValueError:
        return None

    if end_min > start_min:
        return (start_min, end_min)

    # If default mapping yields invalid ordering, try other reasonable combinations
    candidates: List[Tuple[int, int]] = []
    for sa in ("am", "pm"):
        for ea in ("am", "pm"):
            try:
                sm = time_to_minutes(start_hhmm, sa)
                em = time_to_minutes(end_hhmm, ea)
            except ValueError:
                continue
            if em > sm and 0 < (em - sm) <= 12 * 60:
                candidates.append((sm, em))
    if candidates:
        # choose the smallest positive duration
        candidates.sort(key=lambda t: t[1] - t[0])
        return candidates[0]

    return None


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main(
    input_json: str = "data/websoc_raw.json",
    output_csv: str = "data/meetings.csv",
) -> None:
    in_path = Path(input_json)
    out_path = Path(output_csv)

    data = load_json(in_path)
    if not isinstance(data, list):
        raise ValueError("Expected the input JSON to be a list of course/section objects.")

    total_input_entries = len(data)

    rows: List[Dict[str, Any]] = []
    skipped = {
        "missing_days": 0,
        "bad_time": 0,
        "bad_location": 0,
        "tba_or_online": 0,
        "missing_course": 0,
    }

    for obj in data:
        if not isinstance(obj, dict):
            continue

        course_code = str(obj.get("courseCode") or "").strip()
        title = str(obj.get("courseTitle") or "").strip()
        dept = str(obj.get("departmentName") or "").strip()
        section_code = str(obj.get("sectionCode") or "").strip()
        section_type = str(obj.get("sectionType") or "").strip()
        section_num = str(obj.get("sectionNum") or "").strip()
        term = str(obj.get("term") or "").strip()

        days_raw = str(obj.get("days") or "").strip()
        time_raw = str(obj.get("meetingTime") or "").strip()
        loc_raw = str(obj.get("location") or "").strip()

        if not course_code:
            skipped["missing_course"] += 1
            continue

        # If any of days/time/location is explicitly TBA/ONLINE/etc, count as tba_or_online
        tba_like = {"TBA", "ONLINE", "REMOTE", "WEB", "ARR"}
        if (
            days_raw.strip().upper() in tba_like
            or time_raw.strip().upper() in tba_like
            or loc_raw.strip().upper() in tba_like
        ):
            skipped["tba_or_online"] += 1
            continue

        days = normalize_days(days_raw)
        if not days:
            skipped["missing_days"] += 1
            continue

        time_parsed = parse_meeting_time(time_raw)
        if not time_parsed:
            skipped["bad_time"] += 1
            continue
        start_min, end_min = time_parsed

        building_code, room = parse_location(loc_raw)
        if not building_code:
            skipped["bad_location"] += 1
            continue

        # meeting_id: make it unique + stable
        # Example: WRITING_250A-33800-Sem-A
        meeting_id = f"{course_code.replace(' ', '_')}-{section_code}"
        if section_type or section_num:
            meeting_id += f"-{section_type}-{section_num}"

        row = {
            "meeting_id": meeting_id,
            "course_id": course_code,
            "title": title,
            "dept": dept,
            "days": days,
            "start_min": start_min,
            "end_min": end_min,
            "building_code": building_code,
            "room": room,
            "term": term,
        }
        rows.append(row)

    write_csv(out_path, rows)
    print(f"Total input entries: {total_input_entries}")
    print(f"Wrote {len(rows)} meeting rows to {out_path}")
    print("Skipped:")
    for k, v in skipped.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
