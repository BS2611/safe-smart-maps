"""Route A vs Route B continuity comparison. SYNTHETIC TEST/DEMO scores, not real data, no network.

Run from the repo root:  python -m scripts.demo_continuity
"""
from server.services.continuity import compute_continuity
from server.services.scoring_config import load_scoring_config
from tests.test_continuity import route

# 20 segments x 50 m = 1 km each.
A_SCORES = [68] * 20                                             # moderately good, consistent
B_SCORES = [88] * 7 + [28] * 6 + [88] * 7                        # strong ends, 300 m weak stretch
B_COVERED = [True] * 7 + [False] * 6 + [True] * 7


def main() -> None:
    cfg = load_scoring_config()
    print("SYNTHETIC DEMO DATA (not real places or roads)")
    for name, scores, cov in (("Route A", A_SCORES, None), ("Route B", B_SCORES, B_COVERED)):
        r = compute_continuity(cfg, route(scores, covered=cov))
        print(f"{name}: average={r.average_score:.1f} worst_window={r.worst_window_score:.1f} "
              f"coverage={r.coverage_pct:.0f}% longest_gap={r.longest_gap_m:.0f} m "
              f"penalty={r.gap_penalty_applied:.1f} route_score={r.route_score:.1f}")
        for n in r.notes:
            print(f"   - {n}")


if __name__ == "__main__":
    main()
