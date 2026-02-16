from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import Building, Meeting, RankedResult


@dataclass(frozen=True)
class RankConfig:
    # Filtering
    time_window_min: int = 60          # only consider meetings starting within next 60 min
    max_distance_m: float = 1200.0     # only consider meetings within 1.2 km

    # Scoring weights
    w_time: float = 0.6
    w_dist: float = 0.4


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance between two points on Earth in meters.
    """
    R = 6371000.0  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def occurs_today(meeting: Meeting, day_token: str) -> bool:
    """
    day_token: 'M','Tu','W','Th','F','Sa','Su'
    meeting.days: compact like 'MWF' or 'TuTh'
    """
    return day_token in meeting.days


def minutes_until_start(meeting: Meeting, now_min: int) -> int:
    return meeting.start_min - now_min


def filter_candidates(
    meetings: List[Meeting],
    buildings: Dict[str, Building],
    user_latlon: Tuple[float, float],
    day_token: str,
    now_min: int,
    cfg: RankConfig,
) -> List[Tuple[Meeting, int, float]]:
    """
    Returns list of tuples: (meeting, minutes_until_start, distance_m)
    Filters:
      - occurs on day_token
      - starts within [0, cfg.time_window_min]
      - distance <= cfg.max_distance_m
      - building exists
    """
    # Stub for now — implement in Step 3.
    raise NotImplementedError


def score_candidate(
    min_until: int,
    dist_m: float,
    cfg: RankConfig,
) -> Tuple[float, float, float]:
    """
    Returns (final_score, time_score, dist_score).
    time_score and dist_score are normalized to [0,1].
    """
    # Stub for now — implement in Step 3.
    raise NotImplementedError


def rank_meetings(
    meetings: List[Meeting],
    buildings: Dict[str, Building],
    user_latlon: Tuple[float, float],
    day_token: str,
    now_min: int,
    cfg: RankConfig,
    top_k: int = 10,
) -> List[RankedResult]:
    """
    End-to-end ranking: filter -> score -> sort desc -> return top_k results.
    """
    # Stub for now — implement in Step 3.
    raise NotImplementedError
