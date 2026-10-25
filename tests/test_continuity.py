"""Continuity metrics. Segment scores below are SYNTHETIC TEST DATA (no providers, no network)."""
import copy
import unittest
from datetime import datetime, timezone

from server.services.continuity import ContinuityResult, check_continuity_params, compute_continuity
from server.services.scoring_config import ScoringConfigError, load_scoring_config
from server.services.segment_scoring import SegmentScore
from server.services.segmenter import Segment

CFG = load_scoring_config()
T0 = datetime(2026, 10, 24, 20, 0, tzinfo=timezone.utc)


def route(scores, lengths=None, covered=None):
    """scores: list of float|None; lengths default 50 m; covered default True where score known."""
    lengths = lengths or [50.0] * len(scores)
    if covered is None:
        covered = [None if s is None else True for s in scores]
    out, offset = [], 0.0
    for i, (sc, ln, cv) in enumerate(zip(scores, lengths, covered)):
        p = (37.8, -122.45)
        seg = Segment(i, f"seg-{i}", p, p, p, ln, (p, p), offset)
        out.append(SegmentScore(seg, T0, sc, "unknown" if sc is None else "green", {}, [], [],
                                0.0 if sc is None else 1.0, None, cv))
        offset += ln
    return out


def run(scores, **kw):
    return compute_continuity(CFG, route(scores, **kw))


class MetricTests(unittest.TestCase):
    def test_consistently_high(self):
        r = run([80] * 8)
        self.assertAlmostEqual(r.average_score, 80)
        self.assertAlmostEqual(r.worst_window_score, 80)
        self.assertEqual(r.gap_penalty, 0)
        self.assertAlmostEqual(r.route_score, 80)
        self.assertEqual(r.coverage_pct, 100)

    def test_consistently_low(self):
        r = run([20] * 8)
        self.assertAlmostEqual(r.route_score, 20)

    def test_high_average_with_long_weak_stretch(self):
        scores = [90, 90, 90, 90, 90, 90, 10, 10, 10, 10, 90, 90, 90, 90, 90, 90]
        cov = [True] * 6 + [False] * 4 + [True] * 6
        r = run(scores, covered=cov)
        self.assertAlmostEqual(r.average_score, 70)
        self.assertAlmostEqual(r.worst_window_score, 10)
        self.assertAlmostEqual(r.longest_gap_m, 200)
        self.assertAlmostEqual(r.gap_penalty, 5.0)            # (200-150)*0.1
        self.assertAlmostEqual(r.route_score, 0.5 * 70 + 0.5 * 10 - 5)
        self.assertEqual((r.gap_start_m, r.gap_end_m), (300, 500))

    def test_alternating(self):
        r = run([90, 10] * 6, covered=[True, False] * 6)
        self.assertAlmostEqual(r.average_score, 50)
        self.assertAlmostEqual(r.worst_window_score, 50)
        self.assertEqual(r.longest_gap_m, 50)                 # runs never join
        self.assertEqual(r.gap_penalty, 0)

    def test_one_short_weak_segment(self):
        r = run([80, 80, 20, 80, 80, 80, 80, 80], covered=[True, True, False] + [True] * 5)
        self.assertEqual(r.longest_gap_m, 50)
        self.assertEqual(r.gap_penalty, 0)
        self.assertAlmostEqual(r.worst_window_score, (80 * 3 + 20) / 4)

    def test_gap_longer_than_limit_penalized_gap_at_limit_not(self):
        at = run([50] * 6, covered=[True] * 3 + [False] * 3)          # exactly 150 m
        over = run([50] * 7, covered=[True] * 3 + [False] * 4)        # 200 m
        self.assertEqual(at.longest_gap_m, 150)
        self.assertEqual(at.gap_penalty, 0)
        self.assertAlmostEqual(over.gap_penalty, 5.0)

    def test_route_shorter_than_window(self):
        r = run([60, 40, 80])                                  # 150 m
        self.assertAlmostEqual(r.worst_window_score, 60)
        self.assertEqual((r.worst_window_start_m, r.worst_window_end_m), (0, 150))

    def test_route_exactly_window(self):
        r = run([60, 40, 80, 20])
        self.assertAlmostEqual(r.worst_window_score, 50)
        self.assertEqual(r.worst_window_end_m, 200)

    def test_route_longer_than_window(self):
        r = run([100, 100, 100, 100, 0, 0, 100, 100, 100, 100])
        self.assertAlmostEqual(r.worst_window_score, 50)      # 100 m of zeros in any 200 m window
        self.assertAlmostEqual(r.worst_window_end_m - r.worst_window_start_m, 200)

    def test_unequal_segment_lengths_weighted_by_length(self):
        r = compute_continuity(CFG, route([100, 0], lengths=[150.0, 50.0]))
        self.assertAlmostEqual(r.average_score, 75)            # not 50
        self.assertAlmostEqual(r.worst_window_score, 75)       # whole 200 m route

    def test_window_is_not_four_segments_when_lengths_vary(self):
        # 30 m x 10 segments; low segments at index 3-4 (offset 90-150, 60 m); a 200 m window holds
        # 6.67 segments, so a 4-segment (120 m) window would give the wrong answer.
        scores = [100, 100, 100, 0, 0, 100, 100, 100, 100, 100]
        r = compute_continuity(CFG, route(scores, lengths=[30.0] * 10))
        self.assertAlmostEqual(r.worst_window_score, 100 * 140 / 200)
        self.assertAlmostEqual(r.worst_window_end_m - r.worst_window_start_m, 200)

    def test_worst_window_at_start(self):
        r = run([0, 0, 0, 0, 100, 100, 100, 100, 100, 100])
        self.assertAlmostEqual(r.worst_window_score, 0)
        self.assertEqual(r.worst_window_start_m, 0)

    def test_worst_window_in_middle(self):
        r = run([100, 100, 100, 0, 0, 0, 0, 100, 100, 100, 100])
        self.assertAlmostEqual(r.worst_window_score, 0)
        self.assertEqual(r.worst_window_start_m, 150)

    def test_worst_window_at_end(self):
        r = run([100] * 6 + [0] * 4)
        self.assertAlmostEqual(r.worst_window_score, 0)
        self.assertEqual(r.worst_window_end_m, 500)

    def test_window_between_boundaries_is_found(self):
        # a window that straddles segment boundaries in an unaligned way (unequal lengths)
        r = compute_continuity(CFG, route([100, 0, 100], lengths=[120.0, 70.0, 120.0]))
        # best window start minimizes overlap with the 0-score segment's neighbours: 200 m window
        # covers all 70 m of zeros plus 130 m of 100s -> 65
        self.assertAlmostEqual(r.worst_window_score, 65)


class UnknownTests(unittest.TestCase):
    def test_some_unknown_not_treated_as_zero(self):
        r = run([80, None, 80, None, 80, 80])
        self.assertAlmostEqual(r.average_score, 80)
        self.assertAlmostEqual(r.worst_window_score, 80)
        self.assertAlmostEqual(r.route_score, 80)
        self.assertEqual(r.unknown_length_m, 100)
        self.assertTrue(any("not sure" in n for n in r.notes))
        self.assertFalse(r.insufficient_data)

    def test_all_unknown(self):
        r = run([None] * 5)
        self.assertIsNone(r.route_score)
        self.assertIsNone(r.average_score)
        self.assertIsNone(r.worst_window_score)
        self.assertIsNone(r.coverage_pct)
        self.assertTrue(r.insufficient_data)
        self.assertEqual(r.longest_gap_m, 0)
        d = r.to_dict()
        self.assertIsNone(d["route_score"])
        self.assertTrue(d["continuity"]["insufficient_data"])

    def test_known_low_differs_from_unknown(self):
        low = run([10] * 4)
        unk = run([None] * 4)
        self.assertEqual(low.route_score, 10)
        self.assertIsNone(unk.route_score)
        self.assertFalse(low.insufficient_data)
        self.assertEqual(low.unknown_length_m, 0)

    def test_unknown_coverage_does_not_extend_or_create_gap(self):
        r = run([50] * 6, covered=[False, False, None, False, False, False])
        self.assertEqual(r.longest_gap_m, 150)                # run after the unknown
        self.assertAlmostEqual(r.coverage_pct, 0)
        self.assertAlmostEqual(r.coverage_known_pct, 100 * 250 / 300)

    def test_unknown_coverage_everywhere(self):
        r = run([50] * 4, covered=[None] * 4)
        self.assertIsNone(r.coverage_pct)
        self.assertIsNone(r.meets_coverage_target)
        self.assertEqual(r.longest_gap_m, 0)
        self.assertIsNotNone(r.route_score)


class CoverageTests(unittest.TestCase):
    def test_coverage_pct_by_length(self):
        r = compute_continuity(CFG, route([50, 50], lengths=[150.0, 50.0], covered=[True, False]))
        self.assertAlmostEqual(r.coverage_pct, 75)
        self.assertFalse(r.meets_coverage_target)             # target 80
        self.assertTrue(any("below" in n for n in r.notes))

    def test_coverage_target_met(self):
        r = run([50] * 5, covered=[True] * 4 + [False])
        self.assertAlmostEqual(r.coverage_pct, 80)
        self.assertTrue(r.meets_coverage_target)

    def test_longest_gap_in_meters_with_unequal_lengths(self):
        r = compute_continuity(CFG, route([50] * 5, lengths=[40.0, 70.0, 30.0, 90.0, 40.0],
                                          covered=[True, False, False, True, False]))
        self.assertAlmostEqual(r.longest_gap_m, 100)          # 70 + 30, not 2 segments, not 40
        self.assertEqual((r.gap_start_m, r.gap_end_m), (40, 140))

    def test_longest_of_several_gaps(self):
        r = run([50] * 8, covered=[False, True, False, False, True, False, False, False])
        self.assertEqual(r.longest_gap_m, 150)
        self.assertEqual(r.gap_start_m, 250)


class BoundsTests(unittest.TestCase):
    def test_penalty_bounded_by_base_and_score_in_range(self):
        r = run([10] * 40, covered=[False] * 40)              # 2000 m gap -> formula 185
        self.assertAlmostEqual(r.gap_penalty, 185)
        self.assertAlmostEqual(r.gap_penalty_applied, 10)     # capped at the base score
        self.assertEqual(r.route_score, 0)

    def test_score_never_leaves_range(self):
        for scores in ([0] * 6, [100] * 6, [100, 0] * 6):
            for cov in (True, False):
                r = run(scores, covered=[cov] * len(scores))
                self.assertGreaterEqual(r.route_score, 0)
                self.assertLessEqual(r.route_score, 100)

    def test_penalty_uses_config_values(self):
        cfg = copy.deepcopy(CFG)
        cfg["continuity"].update(gap_limit_m=50, gap_penalty_per_m=0.2)
        r = compute_continuity(cfg, route([80] * 4, covered=[False] * 4))
        self.assertAlmostEqual(r.gap_penalty, (200 - 50) * 0.2)

    def test_empty_route(self):
        r = compute_continuity(CFG, [])
        self.assertEqual(r.route_length_m, 0)
        self.assertIsNone(r.route_score)
        self.assertIsNone(r.coverage_pct)
        self.assertEqual(r.to_dict()["continuity"]["longest_gap_m"], 0)

    def test_single_segment(self):
        r = run([70])
        self.assertAlmostEqual(r.route_score, 70)
        self.assertAlmostEqual(r.worst_window_score, 70)
        self.assertEqual(r.worst_window_end_m, 50)

    def test_single_uncovered_segment(self):
        r = run([70], covered=[False])
        self.assertEqual(r.longest_gap_m, 50)
        self.assertEqual(r.gap_penalty, 0)

    def test_unordered_segments_rejected(self):
        segs = route([50, 50, 50])
        with self.assertRaises(ValueError):
            compute_continuity(CFG, [segs[1], segs[0], segs[2]])

    def test_deterministic(self):
        a, b = run([90, 10, 40, 70, 20, 80]), run([90, 10, 40, 70, 20, 80])
        self.assertEqual(a, b)


class DemoComparisonTests(unittest.TestCase):
    """Synthetic Route A (consistent) vs Route B (higher average, one 300 m weak stretch)."""

    def test_gap_exposes_route_b(self):
        from scripts.demo_continuity import A_SCORES, B_COVERED, B_SCORES
        a = compute_continuity(CFG, route(A_SCORES))
        b = compute_continuity(CFG, route(B_SCORES, covered=B_COVERED))
        self.assertGreater(b.average_score, a.average_score)      # B looks better on average
        self.assertLess(b.worst_window_score, a.worst_window_score)
        self.assertEqual(a.longest_gap_m, 0)
        self.assertEqual(b.longest_gap_m, 300)
        self.assertGreater(b.gap_penalty_applied, 0)
        self.assertLess(b.route_score, a.route_score)             # continuity reverses the ranking


class ConfigTests(unittest.TestCase):
    def test_missing_section(self):
        cfg = copy.deepcopy(CFG)
        del cfg["continuity"]
        with self.assertRaises(ScoringConfigError):
            check_continuity_params(cfg)

    def test_weights_must_sum_to_one(self):
        cfg = copy.deepcopy(CFG)
        cfg["continuity"]["avg_weight"] = 0.9
        with self.assertRaises(ScoringConfigError):
            check_continuity_params(cfg)

    def test_bad_window(self):
        cfg = copy.deepcopy(CFG)
        cfg["continuity"]["window_m"] = 0
        with self.assertRaises(ScoringConfigError):
            check_continuity_params(cfg)


class ToDictTests(unittest.TestCase):
    def test_contract_shape(self):
        d = run([80] * 6, covered=[True] * 3 + [False] * 3).to_dict()
        self.assertEqual(set(d), {"route_score", "continuity"})
        for key in ("coverage_pct", "longest_gap_m", "longest_gap_note", "worst_window_score"):
            self.assertIn(key, d["continuity"])
        self.assertEqual(d["continuity"]["longest_gap_note"], "from 150 m to 300 m along the route")
        self.assertEqual(d["continuity"]["coverage_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()
