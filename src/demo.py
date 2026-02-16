from __future__ import annotations

from .io import load_buildings_csv, load_meetings_csv
from .ranker import RankConfig, rank_meetings


def main() -> None:
    buildings = load_buildings_csv("data/buildings.csv")
    meetings = load_meetings_csv("data/meetings.csv")

    # Hardcoded demo scenario (change later)
    user_latlon = (33.6430, -117.8419)  # near DBH (example)
    day_token = "W"
    now_min = 13 * 60 + 10  # 1:10pm

    cfg = RankConfig()

    results = rank_meetings(
        meetings=meetings,
        buildings=buildings,
        user_latlon=user_latlon,
        day_token=day_token,
        now_min=now_min,
        cfg=cfg,
        top_k=10,
    )

    for r in results:
        m = r.meeting
        print(
            f"{m.course_id:12s} {m.days:6s} {m.start_min:4d}-{m.end_min:4d} "
            f"{m.building_code:5s} {m.room:6s} "
            f"dist={r.distance_m:7.1f}m  in={r.minutes_until_start:3d}m  "
            f"score={r.score:.3f} (t={r.time_score:.3f}, d={r.dist_score:.3f})"
        )


if __name__ == "__main__":
    main()
