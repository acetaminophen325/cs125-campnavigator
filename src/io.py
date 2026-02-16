from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from .models import Building, Meeting


def load_buildings_csv(path: str | Path) -> Dict[str, Building]:
    """
    Reads data/buildings.csv with header: code,name,lat,lon
    Returns dict keyed by building code.
    """
    p = Path(path)
    out: Dict[str, Building] = {}

    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("code") or "").strip()
            if not code:
                continue
            out[code] = Building(
                code=code,
                name=(row.get("name") or "").strip(),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
            )
    return out


def load_meetings_csv(path: str | Path) -> List[Meeting]:
    """
    Reads data/meetings.csv with header:
    meeting_id,course_id,title,dept,days,start_min,end_min,building_code,room,term
    """
    p = Path(path)
    out: List[Meeting] = []

    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append(
                Meeting(
                    meeting_id=(row["meeting_id"] or "").strip(),
                    course_id=(row["course_id"] or "").strip(),
                    title=(row["title"] or "").strip(),
                    dept=(row["dept"] or "").strip(),
                    days=(row["days"] or "").strip(),
                    start_min=int(row["start_min"]),
                    end_min=int(row["end_min"]),
                    building_code=(row["building_code"] or "").strip(),
                    room=(row["room"] or "").strip(),
                    term=(row["term"] or "").strip(),
                )
            )
    return out
