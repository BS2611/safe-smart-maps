"""Segment context matching + scoring. All data below are TEST FIXTURES (no network)."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from server.data.models import AreaContext, HelpPoint, Place, RoadContext
from server.services.scoring_config import ScoringConfigError, load_scoring_config
from server.services.segment_scoring import SegmentScorer, check_scoring_params
from server.services.segmenter import segment_route

CFG = load_scoring_config()
PT = ZoneInfo("America/Los_Angeles")
EVENING = datetime(2026, 10, 24, 20, 0, tzinfo=PT)      # Saturday 8 PM
MORNING = datetime(2026, 10, 24, 9, 0, tzinfo=PT)
FETCHED = datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc)
M = 1 / 111_195
LNG = -122.45
SEG = segment_route([(37.8, LNG), (37.8 + 50 * M, LNG)])[0]   # 50 m segment, midpoint 25 m north


def north(m, east_m=0.0):
    return (37.8 + m * M, LNG + east_m * M * 1.26)


def place(m_north=25, east_m=0.0, hours="evening", name="p"):
    wh = {"evening": {d: [(17 * 60, 23 * 60)] for d in range(7)},
          "morning": {d: [(6 * 60, 12 * 60)] for d in range(7)},
          None: None}[hours]
    lat, lng = north(m_north, east_m)
    return Place(name=name, lat=lat, lng=lng, category="cafe", source="test", fetched_at=FETCHED,
                 weekly_hours=wh, is_24h=None)


def road(road_class="primary", lit="yes", east_m=0.0):
    return RoadContext(coordinates=(north(-20, east_m), north(80, east_m)), road_class=road_class,
                       lit=lit, source="test", fetched_at=FETCHED)


def help_point(m_north=25, east_m=0.0, type="police"):
    lat, lng = north(m_north, east_m)
    return HelpPoint(type=type, lat=lat, lng=lng, source="test", fetched_at=FETCHED)


def area(roads=(), helps=()):
    return AreaContext(roads=list(roads), help_points=list(helps), fetched_at=FETCHED)


def score(places=(), ctx=None, arrival=EVENING, cfg=CFG, weights=None):
    ctx = area() if ctx is None else ctx
    return SegmentScorer(cfg, list(places) if places is not None else None, ctx, weights).score_segment(SEG, arrival)


class PlaceTests(unittest.TestCase):
    def test_nearby_open(self):
        f = score([place()]).factors["open_places"]
        self.assertEqual(f.value, 50)
        self.assertEqual(f.evidence["open"], 1)

    def test_nearby_closed(self):
        f = score([place(hours="morning")]).factors["open_places"]
        self.assertEqual((f.value, f.evidence["closed"]), (0, 1))

    def test_unknown_hours_is_not_closed_and_not_open(self):
        f = score([place(hours=None)]).factors["open_places"]
        self.assertEqual(f.value, 0)
        self.assertEqual(f.evidence["unknown_hours"], 1)
        self.assertEqual(f.evidence["closed"], 0)
        self.assertIn("hours not sure", f.reason)

    def test_unknown_hours_does_not_erase_open_count(self):
        f = score([place(), place(hours=None)]).factors["open_places"]
        self.assertEqual((f.value, f.evidence["unknown_hours"]), (50, 1))

    def test_outside_threshold(self):
        f = score([place(east_m=80)]).factors["open_places"]       # ~80 m east of the segment
        self.assertEqual(f.value, 0)
        self.assertEqual(f.evidence["open"], 0)

    def test_multiple_places_table(self):
        vals = [score([place() for _ in range(n)]).factors["open_places"].value for n in (0, 1, 2, 3, 7)]
        self.assertEqual(vals, [0, 50, 75, 100, 100])

    def test_arrival_time_changes_result(self):
        p = [place()]
        self.assertEqual(score(p, arrival=EVENING).factors["open_places"].value, 50)
        self.assertEqual(score(p, arrival=MORNING).factors["open_places"].value, 0)

    def test_place_dataset_unavailable_is_unknown(self):
        f = score(None).factors["open_places"]
        self.assertIsNone(f.value)

    def test_empty_available_dataset_is_zero(self):
        self.assertEqual(score([]).factors["open_places"].value, 0)


class RoadTests(unittest.TestCase):
    def f(self, **kw):
        r = score(ctx=area([road(**kw)]))
        return r.factors["lighting"], r.factors["main_road"]

    def test_lit_yes(self):
        self.assertEqual(self.f(lit="yes")[0].value, 100)

    def test_lit_no(self):
        self.assertEqual(self.f(lit="no")[0].value, 0)

    def test_lit_unknown(self):
        self.assertIsNone(self.f(lit="unknown")[0].value)

    def test_main_road_classes(self):
        for cls, want in [("primary", 100), ("trunk", 100), ("secondary", 100), ("tertiary", 100),
                          ("residential", 60), ("service", 40), ("pedestrian", 40)]:
            self.assertEqual(self.f(road_class=cls)[1].value, want, cls)

    def test_motorway_other_unknown_class_are_unknown(self):
        for cls in ("motorway", "other", "unknown"):
            self.assertIsNone(self.f(road_class=cls)[1].value, cls)

    def test_missing_road_context(self):
        for ctx in (area(), area([road(east_m=60)]), None):     # empty, too far (>25 m), unavailable
            r = score(ctx=ctx) if ctx is not None else SegmentScorer(CFG, [], None).score_segment(SEG, EVENING)
            self.assertIsNone(r.factors["lighting"].value)
            self.assertIsNone(r.factors["main_road"].value)

    def test_nearest_road_wins(self):
        r = score(ctx=area([road("service", "no", east_m=15), road("primary", "yes", east_m=3)]))
        self.assertEqual(r.factors["main_road"].value, 100)


class HelpTests(unittest.TestCase):
    def h(self, helps):
        return score(ctx=area(helps=helps)).factors["help_points"]

    def test_nearby(self):
        f = self.h([help_point(25, 0)])          # segment passes it
        self.assertAlmostEqual(f.value, 100, delta=1)

    def test_linear_distance(self):
        f = self.h([help_point(25, 75)])   # ~75 m east
        self.assertAlmostEqual(f.value, 50, delta=2)

    def test_distant(self):
        self.assertEqual(self.h([help_point(25, 400)]).value, 0)

    def test_none_in_available_area_is_zero(self):
        f = self.h([])
        self.assertEqual(f.value, 0)
        self.assertIn("queried area", f.reason)

    def test_area_unavailable_is_unknown(self):
        r = SegmentScorer(CFG, [], None).score_segment(SEG, EVENING)
        self.assertIsNone(r.factors["help_points"].value)

    def test_multiple_types_nearest_wins(self):
        f = self.h([help_point(25, 120, "hospital"), help_point(25, 20, "fire_station")])
        self.assertEqual(f.evidence["type"], "fire_station")
        self.assertGreater(f.value, 80)


class ScoreTests(unittest.TestCase):
    def best(self):
        return score([place() for _ in range(3)], area([road()], [help_point(25, 0)]))

    def weak(self):
        return score([], area([road("service", "no")], [help_point(25, 400)]))

    def test_weights_come_from_config(self):
        cfg = copy.deepcopy(CFG)
        cfg["weights"] = {k: 0.0 for k in cfg["weights"]}
        cfg["weights"]["lighting"] = 1.0
        r = score(ctx=area([road(lit="yes")]), cfg=cfg)
        self.assertEqual(r.score, 100)                    # only lighting counts
        self.assertAlmostEqual(r.known_weight_fraction, 1.0)

    def test_formula_matches_renormalized_sum(self):
        r = self.weak()
        w = CFG["weights"]
        known = {"open_places": 0, "lighting": 0, "main_road": 40, "help_points": 0, "turns": 100}
        want = sum(w[k] * v for k, v in known.items()) / sum(w[k] for k in known)
        self.assertAlmostEqual(r.score, want)

    def test_ranges(self):
        for r in (self.best(), self.weak(), score(None, None)):
            for f in r.factors.values():
                self.assertTrue(f.value is None or 0 <= f.value <= 100)
            self.assertTrue(r.score is None or 0 <= r.score <= 100)

    def test_all_positive(self):
        r = self.best()
        self.assertGreaterEqual(r.score, 90)
        self.assertEqual(r.band, "green")
        self.assertEqual(sorted(r.unknown_factors), ["activity", "incidents", "transit"])

    def test_weak_context(self):
        r = self.weak()
        self.assertEqual(r.band, "red")
        self.assertLess(r.score, 40)

    def test_nothing_known(self):
        r = SegmentScorer(CFG, None, None).score_segment(SEG, EVENING)
        self.assertAlmostEqual(r.score, 100)          # a straight walk is a known turn factor
        self.assertEqual(r.band, "green")
        self.assertNotIn("turns", r.unknown_factors)
        self.assertEqual(len(r.unknown_factors), 7)
        self.assertAlmostEqual(r.known_weight_fraction, CFG["weights"]["turns"])
        self.assertEqual(r.to_dict()["score"], 100.0)

    def test_unknown_not_treated_as_zero(self):
        lit_unknown = score(ctx=area([road(lit="unknown")]))
        lit_no = score(ctx=area([road(lit="no")]))
        self.assertGreater(lit_unknown.score, lit_no.score)
        self.assertIn("lighting", lit_unknown.unknown_factors)

    def test_more_open_places_raises_score(self):
        ctx = area([road()], [help_point(25, 0)])
        scores = [score([place() for _ in range(n)], ctx).score for n in range(4)]
        self.assertEqual(scores, sorted(scores))
        self.assertLess(scores[0], scores[3])

    def test_band_thresholds(self):
        cfg = copy.deepcopy(CFG)
        cfg["weights"] = {k: 0.0 for k in cfg["weights"]}
        cfg["weights"]["main_road"] = 1.0
        for cls, band in [("primary", "green"), ("residential", "yellow"), ("service", "yellow")]:
            self.assertEqual(score(ctx=area([road(cls)]), cfg=cfg).band, band)
        cfg["bands"] = {"green_min": 90, "yellow_min": 70}
        self.assertEqual(score(ctx=area([road("residential")]), cfg=cfg).band, "red")

    def test_weights_override_renormalized(self):
        w = dict(CFG["weights"])
        w["lighting"] = 2.0
        r = score(ctx=area([road(lit="yes")]), weights=w)
        self.assertTrue(r.score is not None)
        with self.assertRaises(ScoringConfigError):
            score(weights={"lighting": 1.0})

    def test_route_arrival_times_use_walking_speed(self):
        segs = segment_route([(37.8, LNG), (37.8 + 140 * M, LNG)])
        out = SegmentScorer(CFG, [], area()).score_route(segs, EVENING)
        self.assertEqual(out[0].arrival_time, EVENING)
        delta = (out[1].arrival_time - EVENING).total_seconds()
        self.assertAlmostEqual(delta, segs[1].offset_m / 1.4, places=3)

    def test_naive_arrival_rejected(self):
        with self.assertRaises(ValueError):
            score(arrival=datetime(2026, 10, 24, 20))

    def test_contract_dict_shape(self):
        d = self.best().to_dict()
        self.assertEqual(set(d["factors"]), set(CFG["weights"]))
        self.assertNotIn("activity_estimate", d["factors"])
        self.assertEqual(d["start"], [SEG.start[1], SEG.start[0]])
        json.dumps(d)
        self.assertNotIn("safe", " ".join(d["reasons"]).lower())


class ConfigTests(unittest.TestCase):
    def test_real_config_params_valid(self):
        check_scoring_params(CFG)

    def test_invalid_params_rejected(self):
        for mutate in (lambda c: c.pop("bands"), lambda c: c.update(walking_speed_mps=0),
                       lambda c: c["radii_m"].update(road_match=0),
                       lambda c: c["bands"].update(green_min=10)):
            cfg = copy.deepcopy(CFG)
            mutate(cfg)
            with self.assertRaises(ScoringConfigError):
                check_scoring_params(cfg)

    def test_bad_weights_still_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            p.write_text(json.dumps({"version": "t", "weights": {"a": 0.5, "b": 0.6}}), encoding="utf-8")
            with self.assertRaises(ScoringConfigError):
                load_scoring_config(p)


class CoverageFlagTests(unittest.TestCase):
    """SegmentScore.covered: open place or help point within radii_m.coverage (75 m)."""

    def test_open_place_within_75m_covers(self):
        self.assertTrue(score([place(m_north=25, east_m=70)]).covered)

    def test_open_place_beyond_75m_not_covered(self):
        self.assertIs(score([place(m_north=25, east_m=90)]).covered, False)

    def test_closed_place_does_not_cover(self):
        self.assertIs(score([place(hours="morning")]).covered, False)

    def test_unknown_hours_place_is_not_sure(self):
        self.assertIsNone(score([place(hours=None)]).covered)

    def test_help_point_covers(self):
        self.assertTrue(score([], area(helps=[help_point(east_m=70)])).covered)

    def test_unavailable_dataset_is_not_sure(self):
        self.assertIsNone(score(None, area()).covered)
        self.assertIsNone(SegmentScorer(CFG, [], None).score_segment(SEG, EVENING).covered)


if __name__ == "__main__":
    unittest.main()
