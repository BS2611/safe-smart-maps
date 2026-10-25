"""Candidate generation (Mapbox routes + detours) with a fake routing provider. No network."""
import unittest

from server.data.mapbox import MapboxError, RouteCandidate
from server.services.candidates import (
    bearing_deg,
    dedupe,
    detour_points,
    generate_candidates,
    offset_point,
    similar,
)
from server.services.geo import haversine_m
from server.services.scoring_config import load_scoring_config
from tests import fakes

CFG = load_scoring_config()


def shifted(route: RouteCandidate, dlat: float, rid: str) -> RouteCandidate:
    return RouteCandidate(rid, "mapbox", [(lng, lat + dlat) for lng, lat in route.coordinates],
                          route.distance_m, route.duration_s)


class GeometryTests(unittest.TestCase):
    def test_bearing_cardinal_directions(self):
        o = (37.80, -122.45)
        self.assertAlmostEqual(bearing_deg(o, (37.81, -122.45)), 0, delta=0.5)      # north
        self.assertAlmostEqual(bearing_deg(o, (37.80, -122.44)), 90, delta=0.5)     # east
        self.assertAlmostEqual(bearing_deg(o, (37.79, -122.45)), 180, delta=0.5)    # south
        self.assertAlmostEqual(bearing_deg(o, (37.80, -122.46)), 270, delta=0.5)    # west

    def test_offset_point_moves_the_requested_distance(self):
        o = (37.80, -122.45)
        for brg in (0, 90, 200, 315):
            self.assertAlmostEqual(haversine_m(o, offset_point(o, brg, 250.0)), 250.0, delta=1.0)

    def test_detour_points_sit_left_and_right_of_the_middle(self):
        origin, dest = fakes.ORIGIN, fakes.DEST             # due east trip
        left, right = detour_points(origin, dest, 250.0)
        mid_lat = (origin[1] + dest[1]) / 2
        self.assertGreater(left[1], mid_lat)                # left of eastward travel = north
        self.assertLess(right[1], mid_lat)
        self.assertAlmostEqual(left[0], right[0], places=5)

    def test_detour_reach_is_capped_by_a_quarter_of_the_trip_and_has_a_floor(self):
        far_o, far_d = (-122.45, 37.80), (-122.40, 37.80)   # about 4.4 km
        mid = ((far_o[0] + far_d[0]) / 2, 37.80)
        left, _ = detour_points(far_o, far_d, 250.0)
        self.assertAlmostEqual(haversine_m((mid[1], mid[0]), (left[1], left[0])), 250.0, delta=2.0)
        near_o, near_d = (-122.4484, 37.8029), (-122.4480, 37.8029)   # about 35 m
        mid2 = ((near_o[0] + near_d[0]) / 2, 37.8029)
        left2, _ = detour_points(near_o, near_d, 250.0)
        self.assertAlmostEqual(haversine_m((mid2[1], mid2[0]), (left2[1], left2[0])), 80.0, delta=1.0)

    def test_points_are_returned_as_lng_lat(self):
        for lng, lat in detour_points(fakes.ORIGIN, fakes.DEST, 250.0):
            self.assertTrue(-123 < lng < -122 and 37 < lat < 38)


class DedupeTests(unittest.TestCase):
    def test_identical_and_nearly_identical_routes_are_similar(self):
        a = fakes.route_b()
        self.assertTrue(similar(a, a, 20.0, 0.9))
        self.assertTrue(similar(a, shifted(a, 0.00005, "x"), 20.0, 0.9))   # about 5 m

    def test_different_streets_are_not_similar(self):
        self.assertFalse(similar(fakes.route_a(), fakes.route_b(), 20.0, 0.9))
        self.assertFalse(similar(fakes.route_b(), shifted(fakes.route_b(), 0.001, "x"), 20.0, 0.9))

    def test_dedupe_keeps_the_first_of_a_group(self):
        a, b = fakes.route_a("first"), fakes.route_b("second")
        dup = shifted(a, 0.00003, "dup-of-first")
        self.assertEqual([c.id for c in dedupe([a, b, dup], CFG)], ["first", "second"])


class GenerateTests(unittest.TestCase):
    def test_main_routes_come_first_then_detours_and_ids_are_unique(self):
        detour = RouteCandidate("mapbox-0", "mapbox", [fakes.ORIGIN, (-122.4460, 37.8100), fakes.DEST],
                                1200.0, 900.0)
        routing = fakes.FakeRouting(detours=[detour])
        out = generate_candidates(routing, fakes.ORIGIN, fakes.DEST, CFG)
        ids = [c.id for c in out]
        self.assertEqual(ids[:2], ["mapbox-0", "mapbox-1"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(out), 3)

    def test_detours_use_forced_waypoints_and_the_main_call_has_none(self):
        routing = fakes.FakeRouting()
        generate_candidates(routing, fakes.ORIGIN, fakes.DEST, CFG)
        self.assertEqual([len(call[2]) for call in routing.calls], [0, 1, 1])

    def test_failing_detours_are_skipped(self):
        out = generate_candidates(fakes.FakeRouting(), fakes.ORIGIN, fakes.DEST, CFG)   # detours say "empty"
        self.assertEqual([c.id for c in out], ["mapbox-0", "mapbox-1"])

    def test_failing_main_request_raises(self):
        routing = fakes.FakeRouting(error=MapboxError("HTTP 500"))
        with self.assertRaises(MapboxError):
            generate_candidates(routing, fakes.ORIGIN, fakes.DEST, CFG)

    def test_detour_that_repeats_a_main_route_is_dropped(self):
        routing = fakes.FakeRouting(detours=[fakes.route_a("again")])
        out = generate_candidates(routing, fakes.ORIGIN, fakes.DEST, CFG)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
