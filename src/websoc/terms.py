import re
from datetime import datetime


def get_current_term() -> str:
    """Current quarter string, e.g. '2026 Winter'."""
    now = datetime.now()
    year = now.year
    month = now.month  # 1-12
    if 1 <= month <= 3:
        return f"{year} Winter"
    if 4 <= month <= 6:
        return f"{year} Spring"
    if 7 <= month <= 9:
        return f"{year} Summer1"
    return f"{year} Fall"


def get_current_term_for_anteater():
    """Return dict with year and quarter for Anteater API, or None."""
    term = get_current_term()
    m = re.match(r"^(\d{4})\s+(Fall|Winter|Spring|Summer1|Summer2|Summer10wk)$", term, re.I)
    if not m:
        return None
    return {"year": m.group(1), "quarter": m.group(2)}
