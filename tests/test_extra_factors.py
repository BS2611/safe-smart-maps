"""Turns, activity, incidents and streetlight-outage handling. Labeled fixtures, no network."""
import unittest
from datetime import datetime

from server.data.sf_open_data import Incident, Outage, SfDataError
from server.services.geo import bearing_deg, turn_angle_deg
from server.services.segment_scoring import SegmentScorer
from server.services.segmenter import segment_route
from tests import fakes
from tests.test_planner import ONE_AM, PlannerCase, request
from tests.test_segment_scoring import CFG, EVENING, LNG, PT, SEG, M, area, north, place, road

PARAMS = CFG["factor_params"]


def incident_at(m_north=25):
    lat, lng = north(m_north)
    return Incident(lng=lng, lat=lat, category="Theft")


def outage_at(m_north=25):
    lat, lng = north(m_north)
    return Outage(lng=lng, lat=lat, reported_at="2026-10-23")


def scorer(places=(), ctx=None, incidents=None, outages=None):
    ctx = area([road()]) if ctx is None else ctx
    return SegmentScorer(CFG, None if places is None else list(places), ctx,
                         incidents=incidents, outages=outages)


class GeoHelpers(unittest.TestCase):
    def test_bearing_and_turn_angle(self):
        origin = (37.8, LNG)
        self.assertAlmostEqual(bearing_deg(origin, (37.9, LNG)), 0, places=3)
        self.assertAlmostEqual(bearing_deg(origin, (37.8, LNG + 0.1)), 90, delta=0.5)
        self.assertEqual(turn_angle_deg(350, 10), 20)
        self.assertEqual(turn_angle_deg(10, 350), 20)
        self.assertEqual(turn_angle_deg(0, 180), 180)


class TurnTests(unittest.TestCase):
    def straight(self):
        return segment_route([(37.8, LNG), (37.8 + 50 * M, LNG), (37.8 + 100 * M, LNG)], 50)

    def corner(self):
        return segment_route([(37.8, LNG), (37.8 + 50 * M, LNG), (37.8 + 50 * M, LNG + 50 * M * 1.26)], 50)

    def test_straight_is_gentle(self):
        segs = self.straight()
        r = scorer().score_segment(segs[1], EVENING, prev=segs[0])
        self.assertEqual(r.factors["turns"].value, PARAMS["turns_by_angle"]["gentle"])

    def test_right_angle_is_sharp(self):
        segs = self.corner()
        r = scorer().score_segment(segs[1], EVENING, prev=segs[0])
        self.assertEqual(r.factors["turns"].value, PARAMS["turns_by_angle"]["sharp"])

    def test_first_segment_has_no_turn(self):
        self.assertEqual(scorer().score_segment(SEG, EVENING).factors["turns"].value, 100)

    def test_score_route_passes_the_previous_segment(self):
        scored = scorer().score_route(self.corner(), EVENING)
        self.assertEqual(scored[0].factors["turns"].value, 100)
        self.assertEqual(scored[-1].factors["turns"].value, PARAMS["turns_by_angle"]["sharp"])

    def test_turns_alone_never_make_a_score(self):
        r = SegmentScorer(CFG, None, None).score_segment(SEG, EVENING)
        self.assertIsNone(r.score)
        self.assertEqual(r.band, "unknown")


class ActivityTests(unittest.TestCase):
    def test_scales_with_open_places(self):
        values = [scorer([place() for _ in range(n)]).score_segment(SEG, EVENING).factors["activity"].value
                  for n in range(6)]
        self.assertEqual(values, [0, 25, 50, 75, 100, 100])

    def test_small_hours_count_for_less(self):
        night = datetime(2026, 10, 25, 1, 0, tzinfo=PT)
        evening_places = [place() for _ in range(4)]
        self.assertGreater(scorer(evening_places).score_segment(SEG, EVENING).factors["activity"].value, 0)
        # evening-only places are closed at 1 AM, so nothing counts
        self.assertEqual(scorer(evening_places).score_segment(SEG, night).factors["activity"].value, 0)

    def test_time_of_day_weight_applies(self):
        late = datetime(2026, 10, 24, 22, 30, tzinfo=PT)   # 22:00 band = 0.8
        p = [place() for _ in range(4)]
        self.assertEqual(scorer(p).score_segment(SEG, late).factors["activity"].value, 80)

    def test_labeled_estimate_and_unknown_without_places(self):
        f = scorer([place()]).score_segment(SEG, EVENING).factors["activity"]
        self.assertIn("estimate", f.reason)
        self.assertIsNone(scorer(None).score_segment(SEG, EVENING).factors["activity"].value)

    def test_closed_places_do_not_count(self):
        v = scorer([place(hours="morning")]).score_segment(SEG, EVENING).factors["activity"].value
        self.assertEqual(v, 0)


class IncidentTests(unittest.TestCase):
    def incidents(self, items):
        return scorer(incidents=items).score_segment(SEG, EVENING).factors["incidents"]

    def test_none_is_not_sure(self):
        self.assertIsNone(self.incidents(None).value)

    def test_empty_list_is_known_clean(self):
        self.assertEqual(self.incidents([]).value, 100)

    def test_nearby_incidents_lower_it_and_far_ones_do_not(self):
        f = self.incidents([incident_at(), incident_at(30), incident_at(500)])
        self.assertEqual(f.value, 100 - 2 * PARAMS["incident_points_each"])

    def test_floor_at_zero(self):
        self.assertEqual(self.incidents([incident_at()] * 30).value, 0)

    def test_low_weight(self):
        self.assertLessEqual(CFG["weights"]["incidents"], 0.05)


class OutageTests(unittest.TestCase):
    def lighting(self, outages, lit="yes"):
        return scorer(ctx=area([road(lit=lit)]), outages=outages).score_segment(SEG, EVENING).factors["lighting"]

    def test_outage_lowers_known_lighting(self):
        hit = self.lighting([outage_at()])
        self.assertEqual(hit.value, 100 - PARAMS["outage_penalty_each"])
        self.assertIn("outage", hit.reason)

    def test_far_outage_ignored_and_floor_is_zero(self):
        self.assertEqual(self.lighting([outage_at(300)]).value, 100)
        self.assertEqual(self.lighting([outage_at()] * 9).value, 0)

    def test_outage_never_turns_not_sure_into_a_number(self):
        self.assertIsNone(self.lighting([outage_at()], lit="unknown").value)

    def test_unavailable_outage_data_changes_nothing(self):
        self.assertEqual(self.lighting(None).value, 100)


class PlannerIntegration(PlannerCase):
    def first_segment(self, **overrides):
        return self.planner(**overrides).plan(request()).routes[0].segments[0]

    def test_without_sf_data_incidents_stay_not_sure(self):
        self.assertIn("incidents", self.first_segment().unknown_factors)

    def test_turns_and_activity_are_now_known(self):
        seg = self.first_segment()
        self.assertNotIn("turns", seg.unknown_factors)
        self.assertNotIn("activity", seg.unknown_factors)

    def test_sf_data_fills_incidents(self):
        seg = self.first_segment(sf=fakes.FakeSf())
        self.assertNotIn("incidents", seg.unknown_factors)
        self.assertEqual(seg.factors["incidents"], 100)

    def test_incidents_along_the_route_lower_the_score(self):
        clean = self.planner(sf=fakes.FakeSf()).plan(request()).routes[0]
        pts = clean.geometry.coordinates
        noisy_sf = fakes.FakeSf(incidents=[Incident(lng=x, lat=y, category="x") for x, y in pts for _ in range(8)])
        noisy = self.planner(sf=noisy_sf).plan(request()).routes[0]
        self.assertLess(noisy.route_score, clean.route_score)

    def test_sf_failure_keeps_going_with_warnings(self):
        resp = self.planner(sf=fakes.FakeSf(error=SfDataError("sf311", "HTTP 500"))).plan(request())
        self.assertTrue(resp.routes)
        self.assertTrue(any("Past incident reports" in w for w in resp.warnings))
        self.assertTrue(any("Streetlight outage reports" in w for w in resp.warnings))
        self.assertIn("incidents", resp.routes[0].segments[0].unknown_factors)

    def test_sf_data_is_cached_between_requests(self):
        sf = fakes.FakeSf()
        planner = self.planner(sf=sf)
        planner.plan(request())
        calls = sf.calls
        planner.plan(request(ONE_AM))
        self.assertEqual(sf.calls, calls)


if __name__ == "__main__":
    unittest.main()
