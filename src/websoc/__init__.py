# UCI WebSoc scraper — drop-in package for use under src.websoc
from .scraper import fetch_class_sessions, to_class_sessions, build_websoc_options
from .anteater import fetch_websoc_from_anteater, fetch_departments_for_term
from .terms import get_current_term, get_current_term_for_anteater

__all__ = [
    "fetch_class_sessions",
    "to_class_sessions",
    "build_websoc_options",
    "fetch_websoc_from_anteater",
    "fetch_departments_for_term",
    "get_current_term",
    "get_current_term_for_anteater",
]
