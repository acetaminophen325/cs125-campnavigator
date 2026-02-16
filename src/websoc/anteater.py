import re
import requests

BASE = "https://anteaterapi.com/v2/rest/websoc"
DEPARTMENTS_URL = "https://anteaterapi.com/v2/rest/websoc/departments"


def _term_to_year_quarter(term: str):
    if not term:
        return None
    m = re.match(r"^(\d{4})\s+(Fall|Winter|Spring|Summer1|Summer2|Summer10wk)$", term, re.I)
    if not m:
        return None
    return {"year": m.group(1), "quarter": m.group(2)}


def fetch_websoc_from_anteater(search_options: dict) -> dict:
    parsed = _term_to_year_quarter(search_options.get("term", ""))
    if not parsed:
        raise ValueError("term must be like '2025 Fall' or '2024 Winter'")

    params = {"year": parsed["year"], "quarter": parsed["quarter"]}
    for key in (
        "department", "ge", "instructorName", "courseNumber", "courseTitle",
        "sectionCodes", "days", "building", "room", "division", "sectionType",
        "startTime", "endTime", "fullCourses", "cancelledCourses",
    ):
        val = search_options.get(key)
        if val is not None and val != "":
            params[key] = val

    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok") or "data" not in data:
        raise RuntimeError("Anteater API returned unexpected shape")
    schools = data.get("data", {}).get("schools") or []
    return {"schools": schools}


def fetch_departments_for_term(year: str, quarter: str) -> list:
    r = requests.get(
        DEPARTMENTS_URL,
        params={"sinceYear": year, "sinceQuarter": quarter},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok") or not isinstance(data.get("data"), list):
        raise RuntimeError("Unexpected departments response")
    return data["data"]


def fetch_class_sessions_from_anteater(search_options: dict) -> list:
    from . import scraper
    raw = fetch_websoc_from_anteater(search_options)
    return scraper.to_class_sessions(raw, search_options.get("term", ""))
