# src/ranker.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import Building, Meeting, RankedResult


@dataclass(frozen=True)
class RankConfig:
    # Filtering
    time_window_min: int = 60          # consider meetings starting within next 60 min
    max_distance_m: float = 1200.0     # consider meetings within 1.2 km

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
    include_ongoing: bool = True,
) -> List[Tuple[Meeting, int, float]]:
    """
    Returns list of tuples: (meeting, minutes_until_start, distance_m)
    Filters:
      - occurs on day_token
      - starts within [0, cfg.time_window_min] or is currently ongoing (if include_ongoing=True)
      - distance <= cfg.max_distance_m
      - building exists
    
    include_ongoing: if True, includes meetings that have already started but not ended.
    """
    user_lat, user_lon = user_latlon
    out: List[Tuple[Meeting, int, float]] = []

    for m in meetings:
        # Must meet today
        if not occurs_today(m, day_token):
            continue

        # Must have building coords
        b = buildings.get(m.building_code)
        if b is None:
            continue

        # Time window: starting soon or currently ongoing
        mins_until = minutes_until_start(m, now_min)
        if mins_until < 0:
            # already started
            if include_ongoing and now_min < m.end_min:
                # Include if meeting is still ongoing (hasn't ended yet)
                pass
            else:
                continue
        if mins_until >= 0 and mins_until > cfg.time_window_min:
            # Not yet started and too far in the future
            continue

        # Distance filter
        dist = haversine_m(user_lat, user_lon, b.lat, b.lon)
        if dist > cfg.max_distance_m:
            continue

        out.append((m, mins_until, dist))

    return out


def score_candidate(
    min_until: int,
    dist_m: float,
    cfg: RankConfig,
) -> Tuple[float, float, float]:
    """
    Returns (final_score, time_score, dist_score).
    time_score and dist_score are normalized to [0,1], higher is better.
    """
    # Normalize time: 0 min until start => best (1.0), cfg.time_window_min => worst (0.0)
    # Guard against zero/negative time_window_min
    if cfg.time_window_min > 0:
        time_score = 1.0 - (min_until / float(cfg.time_window_min))
    else:
        # If time window is not positive, default time_score based on whether meeting is starting soon
        time_score = 1.0 if min_until <= 0 else 0.0
    
    # Clamp to [0,1]
    if time_score < 0.0:
        time_score = 0.0
    elif time_score > 1.0:
        time_score = 1.0

    # Normalize distance: 0m => best (1.0), cfg.max_distance_m => worst (0.0)
    # Guard against zero/negative max_distance_m
    if cfg.max_distance_m > 0:
        dist_score = 1.0 - (dist_m / float(cfg.max_distance_m))
    else:
        # If max distance is not positive, default dist_score based on distance
        dist_score = 1.0 if dist_m == 0 else 0.0
    
    # Clamp to [0,1]
    if dist_score < 0.0:
        dist_score = 0.0
    elif dist_score > 1.0:
        dist_score = 1.0

    final = cfg.w_time * time_score + cfg.w_dist * dist_score
    return final, time_score, dist_score


def rank_meetings(
    meetings: List[Meeting],
    buildings: Dict[str, Building],
    user_latlon: Tuple[float, float],
    day_token: str,
    now_min: int,
    cfg: RankConfig,
    top_k: int = 10,
    include_ongoing: bool = True,
) -> List[RankedResult]:
    """
    End-to-end ranking: filter -> score -> sort desc -> return top_k results.
    
    include_ongoing: if True, includes meetings that are currently in progress.
    """
    candidates = filter_candidates(
        meetings=meetings,
        buildings=buildings,
        user_latlon=user_latlon,
        day_token=day_token,
        now_min=now_min,
        cfg=cfg,
        include_ongoing=include_ongoing,
    )

    ranked: List[RankedResult] = []
    for m, mins_until, dist_m in candidates:
        score, t_score, d_score = score_candidate(mins_until, dist_m, cfg)
        ranked.append(
            RankedResult(
                meeting=m,
                score=score,
                minutes_until_start=mins_until,
                distance_m=dist_m,
                time_score=t_score,
                dist_score=d_score,
            )
        )

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:top_k]

def fmt_time(mins: int) -> str:
    """
    Convert minutes since midnight to a human-readable time like '2:05pm'.
    """
    mins = int(mins)
    h24 = mins // 60
    m = mins % 60
    ampm = "am" if h24 < 12 else "pm"
    h12 = h24 % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d}{ampm}"