"""Prints segment scores for the TEST/DEMO Palace of Fine Arts fixture. No network.

Run from the repo root:  python -m scripts.demo_segment_scoring
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from server.services.segment_scoring import SegmentScorer
from server.services.scoring_config import load_scoring_config
from server.services.segmenter import segment_route
from tests.fixtures import palace_demo as fx


def main() -> None:
    cfg = load_scoring_config()
    segs = segment_route(fx.ROUTE, cfg["segment_length_m"])
    depart = datetime(2026, 10, 24, 20, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    scorer = SegmentScorer(cfg, fx.PLACES, fx.AREA)
    print(f"TEST/DEMO FIXTURE (not real data): {len(segs)} segments, depart {depart:%H:%M}")
    for r in scorer.score_route(segs, depart):
        s = r.segment
        vals = {k: v.value for k, v in r.factors.items() if v.value is not None}
        print(f"{s.segment_id}: {s.length_m:.1f} m score={r.score if r.score is None else round(r.score, 1)} "
              f"band={r.band} known={r.known_weight_fraction:.2f}")
        print(f"   factors={vals} unknown={r.unknown_factors}")
        print(f"   reasons={r.reasons}")


if __name__ == "__main__":
    main()
