"""Planner end to end with labeled fake providers (tests/fakes.py). No network."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.data.mapbox import MapboxError
from server.data.models import BoundingBox
from server.services.planner import (
    PlannerError,
    apply_priorities,
    bbox_of,
    confidence_for,
)
from server.services.schemas import RoutesRequest
from server.services.scoring_config import load_scoring_config
from server.services.wording import find_banned_wording
from tests import fakes

CFG = load_scoring_config()
# 8 PM and 1 AM Pacific on the demo weekend (PDT = UTC-7).
EIGHT_PM = datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc)
ONE_AM = datetime(2026, 10, 25, 8, 0, tzinfo=timezone.utc)


def request(depart=EIGHT_PM, extra=10, priorities=None, origin=fakes.ORIGIN, dest=fakes.DEST):
    return RoutesRequest.model_validate({
        "from": {"lat": origin[1], "lng": origin[0]}, "to": {"lat": dest[1], "lng": dest[0]},
        "depart_time": depart.isoformat(),
        "settings": {"max_extra_minutes": extra, "priorities": priorities or []},
    })


def by_label(resp):
    out = {}
    for r in resp.routes:
        for label in [r.label, *r.also_labels]:
            out[label] = r
    return out


class PlannerCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def planner(self, **overrides):
        return fakes.make_planner(self.dir, **overrides)


class ContractTests(PlannerCase):
    def test_returns_labeled_routes_with_contract_fields(self):
        resp = self.planner().plan(request())
        self.assertEqual((resp.api_version, resp.scoring_version), ("1", "scoring_v1"))
        labels = by_label(resp)
        self.assertEqual(set(labels), {"safest", "balanced", "fastest"})
        fast = labels["fastest"]
        self.assertEqual((fast.duration_min, fast.extra_min, fast.distance_m), (9.0, 0.0, 740))
        seg = fast.segments[0]
        self.assertEqual(seg.segment_id, "seg-0")
        self.assertIn(seg.band, {"green", "yellow", "red", "unknown"})
        self.assertEqual(set(seg.factors), set(CFG["weights"]))
        self.assertEqual(fast.geometry.type, "LineString")
        self.assertEqual(fast.geometry.coordinates[0], fakes.ORIGIN)     # [lng, lat]
        self.assertEqual(seg.start[0], fakes.ORIGIN[0])                  # [lng, lat] in segments too

    def test_data_time_is_the_oldest_source_time(self):
        older = fakes.FETCHED - timedelta(hours=5)
        provider = fakes.make_places_provider(self.dir, fakes.places(), fetched_at=older)
        resp = self.planner(places=provider).plan(request())
        self.assertEqual(resp.data_fetched_at, older)

    def test_unavailable_factors_stay_not_sure_never_zero(self):
        seg = self.planner().plan(request()).routes[0].segments[0]
        for name in CFG["factor_params"]["not_yet_implemented"]:
            self.assertIsNone(seg.factors[name], name)
            self.assertIn(name, seg.unknown_factors)

    def test_wording_has_no_safety_promises(self):
        resp = self.planner().plan(request())
        for route in resp.routes:
            self.assertEqual(find_banned_wording(route.explanation), [])
            for seg in route.segments:
                self.assertEqual(find_banned_wording(" ".join(seg.reasons)), [])


class TimeAwarenessTests(PlannerCase):
    def test_coverage_drops_at_1am_when_the_restaurants_close(self):
        planner = self.planner()
        early = planner.plan(request(EIGHT_PM, extra=20))
        late = planner.plan(request(ONE_AM, extra=20))
        b_early = next(r for r in early.routes if r.route_id == "mapbox-1")
        b_late = next(r for r in late.routes if r.route_id == "mapbox-1")
        self.assertGreater(b_early.continuity.coverage_pct, b_late.continuity.coverage_pct)
        self.assertGreater(b_early.route_score, b_late.route_score)
        self.assertGreater(b_late.continuity.longest_gap_m, b_early.continuity.longest_gap_m)
        self.assertGreater(b_early.open_places_count, b_late.open_places_count)

    def test_lit_main_road_leads_at_8pm_but_loses_its_activity_edge_at_1am(self):
        """With scoring_v1 the lit main road still edges ahead at 1 AM (lighting and road type
        outweigh open places), but its score collapses and the night-owl street is the more
        active one. The test pins that behaviour, it does not claim either route is better."""
        planner = self.planner()
        evening = by_label(planner.plan(request(EIGHT_PM, extra=20)))
        night = by_label(planner.plan(request(ONE_AM, extra=20)))
        self.assertEqual(evening["safest"].route_id, "mapbox-1")
        self.assertGreater(evening["safest"].route_score - evening["fastest"].route_score, 20)
        b_night = next(r for r in night.values() if r.route_id == "mapbox-1")
        a_night = next(r for r in night.values() if r.route_id == "mapbox-0")
        self.assertLess(b_night.route_score, evening["safest"].route_score / 2)
        self.assertGreater(a_night.continuity.coverage_pct, b_night.continuity.coverage_pct)
        self.assertLess(a_night.continuity.longest_gap_m, b_night.continuity.longest_gap_m)

    def test_extra_minutes_cap_limits_the_choice(self):
        resp = self.planner().plan(request(EIGHT_PM, extra=0))
        self.assertEqual(len(resp.routes), 1)
        self.assertEqual(resp.routes[0].label, "safest")
        self.assertEqual(set(resp.routes[0].also_labels), {"balanced", "fastest"})


class MissingDataTests(PlannerCase):
    def test_no_saved_listings_means_not_sure_with_a_warning(self):
        empty = fakes.make_places_provider(self.dir)           # nothing saved: a cache miss
        resp = self.planner(places=empty).plan(request())
        route = resp.routes[0]
        self.assertIsNone(route.open_places_count)
        self.assertIsNone(route.continuity.coverage_pct)
        self.assertIn("open_places", route.segments[0].unknown_factors)
        self.assertTrue(any("not saved for this area" in w for w in resp.warnings))

    def test_places_cache_with_zero_places_is_known_zero_not_unknown(self):
        zero = fakes.make_places_provider(self.dir, [])
        route = self.planner(places=zero).plan(request()).routes[0]
        self.assertEqual(route.open_places_count, 0)
        self.assertEqual(route.segments[0].factors["open_places"], 0.0)
        self.assertEqual(route.continuity.coverage_pct, 0.0)

    def test_osm_failure_makes_lighting_not_sure_and_warns(self):
        resp = self.planner(context=fakes.FakeContext(error=fakes.osm_down())).plan(request())
        seg = resp.routes[0].segments[0]
        for name in ("lighting", "main_road", "help_points"):
            self.assertIn(name, seg.unknown_factors)
        self.assertIsNone(resp.routes[0].nearest_help_point)
        self.assertTrue(any("OpenStreetMap" in w for w in resp.warnings))

    def test_stale_listings_are_used_with_a_warning(self):
        old = datetime.now(timezone.utc) - timedelta(days=3)
        stale = fakes.make_places_provider(self.dir, fakes.places(), fetched_at=old, ttl_seconds=3600)
        resp = self.planner(places=stale).plan(request())
        self.assertTrue(any("older than" in w for w in resp.warnings))
        self.assertEqual(resp.data_fetched_at, old)

    def test_listings_for_only_part_of_the_area_warn(self):
        part = BoundingBox(37.80, -122.45, 37.81, -122.444)    # covers route A's west half only
        provider = fakes.make_places_provider(self.dir, fakes.places(), area=part)
        resp = self.planner(places=provider).plan(request())
        self.assertTrue(any("only part" in w for w in resp.warnings))
        self.assertIsNotNone(resp.routes[0].open_places_count)

    def test_unreadable_opening_hours_are_reported_and_not_counted_as_open(self):
        resp = self.planner().plan(request(EIGHT_PM, extra=20))
        self.assertTrue(any("opening hours we could not read" in w for w in resp.warnings))


class ContextCacheTests(PlannerCase):
    def test_map_data_is_cached_between_requests(self):
        ctx = fakes.FakeContext()
        planner = self.planner(context=ctx)
        planner.plan(request(EIGHT_PM))
        planner.plan(request(ONE_AM))
        self.assertEqual(ctx.calls, 1)

    def test_failed_map_lookup_is_not_cached(self):
        ctx = fakes.FakeContext(error=fakes.osm_down())
        planner = self.planner(context=ctx)
        planner.plan(request())
        planner.plan(request())
        self.assertEqual(ctx.calls, 2)


class RoutingErrorTests(PlannerCase):
    def code(self, error):
        planner = self.planner(routing=fakes.FakeRouting(error=error))
        with self.assertRaises(PlannerError) as cm:
            planner.plan(request())
        return cm.exception

    def test_error_kinds_map_to_api_codes(self):
        cases = [("not_configured", "NOT_CONFIGURED"), ("timeout", "UPSTREAM_TIMEOUT"),
                 ("empty", "NO_ROUTE"), ("failed", "UPSTREAM_ERROR")]
        for kind, code in cases:
            with self.subTest(kind):
                self.assertEqual(self.code(MapboxError("x", kind=kind)).code, code)

    def test_messages_do_not_leak_provider_text(self):
        err = self.code(MapboxError("HTTP 401 pk.secret", kind="failed"))
        self.assertNotIn("pk.secret", err.message)

    def test_no_candidates_is_no_route(self):
        planner = self.planner(routing=fakes.FakeRouting(candidates=[]))
        with self.assertRaises(PlannerError) as cm:
            planner.plan(request())
        self.assertEqual(cm.exception.code, "NO_ROUTE")

    def test_same_place_is_a_bad_request(self):
        with self.assertRaises(PlannerError) as cm:
            self.planner().plan(request(origin=fakes.ORIGIN, dest=(fakes.ORIGIN[0] + 0.00005, fakes.ORIGIN[1])))
        self.assertEqual(cm.exception.code, "BAD_REQUEST")

    def test_too_long_a_trip_is_a_bad_request(self):
        far = fakes.route_a()
        far = type(far)("mapbox-0", "mapbox", [fakes.ORIGIN, (-122.38, 37.86)], 13000.0, 9000.0)
        planner = self.planner(routing=fakes.FakeRouting(candidates=[far]))
        with self.assertRaises(PlannerError) as cm:
            planner.plan(request())
        self.assertEqual(cm.exception.code, "BAD_REQUEST")
        self.assertIn("5 km", cm.exception.message)


class CandidateWiringTests(PlannerCase):
    def test_detours_are_requested_with_waypoints(self):
        routing = fakes.FakeRouting()
        self.planner(routing=routing).plan(request())
        self.assertEqual([len(c[2]) for c in routing.calls], [0, 1, 1])

    def test_detour_routes_become_extra_candidates_with_unique_ids(self):
        detour = fakes.route_b("mapbox-0")
        detour = type(detour)("mapbox-0", "mapbox", [fakes.ORIGIN, (-122.4460, 37.8100), fakes.DEST],
                              1200.0, 900.0)
        routing = fakes.FakeRouting(detours=[detour])
        resp = self.planner(routing=routing).plan(request(extra=20))
        ids = {r.route_id for r in resp.routes}
        self.assertEqual(len(ids), len(resp.routes))

    def test_single_route_answer_still_returns_one_route_with_all_labels(self):
        routing = fakes.FakeRouting(candidates=[fakes.route_a()])
        resp = self.planner(routing=routing).plan(request())
        self.assertEqual(len(resp.routes), 1)
        self.assertEqual(resp.routes[0].label, "safest")


class HelpPointTests(PlannerCase):
    def test_help_point_within_the_radius_is_reported_with_name_and_distance(self):
        resp = self.planner().plan(request(EIGHT_PM, extra=20))
        route_b = next(r for r in resp.routes if r.route_id == "mapbox-1")
        self.assertEqual(route_b.nearest_help_point.name, "Fixture Police Station")
        self.assertLessEqual(route_b.nearest_help_point.distance_m, CFG["radii_m"]["help_point"])

    def test_help_point_beyond_the_radius_is_not_reported(self):
        from dataclasses import replace

        from server.data.models import HelpPoint
        far = HelpPoint("hospital", 37.8300, -122.4000, "osm", fakes.FETCHED, name="Far Hospital")
        ctx = fakes.FakeContext(context=replace(fakes.area_context(), help_points=[far]))
        resp = self.planner(context=ctx).plan(request(EIGHT_PM, extra=20))
        self.assertTrue(all(r.nearest_help_point is None for r in resp.routes))

    def test_unnamed_help_point_uses_its_type(self):
        from dataclasses import replace

        from server.data.models import HelpPoint
        unnamed = HelpPoint("fire_station", 37.8062, -122.4470, "osm", fakes.FETCHED)
        ctx = fakes.FakeContext(context=replace(fakes.area_context(), help_points=[unnamed]))
        resp = self.planner(context=ctx).plan(request(EIGHT_PM, extra=20))
        route_b = next(r for r in resp.routes if r.route_id == "mapbox-1")
        self.assertEqual(route_b.nearest_help_point.name, "fire station")


class DegenerateInputTests(PlannerCase):
    def test_route_with_no_distinct_points_is_skipped_and_others_still_returned(self):
        flat = fakes.RouteCandidate("mapbox-9", "mapbox", [fakes.ORIGIN, fakes.ORIGIN], 10.0, 10.0)
        resp = self.planner(routing=fakes.FakeRouting(candidates=[flat, fakes.route_a()])).plan(request())
        self.assertEqual([r.route_id for r in resp.routes], ["mapbox-1"])

    def test_only_unusable_routes_is_no_route(self):
        flat = fakes.RouteCandidate("mapbox-0", "mapbox", [fakes.ORIGIN, fakes.ORIGIN], 10.0, 10.0)
        with self.assertRaises(PlannerError) as cm:
            self.planner(routing=fakes.FakeRouting(candidates=[flat])).plan(request())
        self.assertEqual(cm.exception.code, "NO_ROUTE")

    def test_value_error_from_routing_is_a_bad_request(self):
        with self.assertRaises(PlannerError) as cm:
            self.planner(routing=fakes.FakeRouting(error=ValueError("origin must be valid"))).plan(request())
        self.assertEqual(cm.exception.code, "BAD_REQUEST")


class ExplainerTests(PlannerCase):
    def test_explainer_gets_computed_facts_only(self):
        explainer = fakes.FakeExplainer(text="Better lit and more active.", source="ai")
        resp = self.planner(explainer=explainer).plan(request())
        self.assertEqual(len(explainer.seen), len(resp.routes))
        self.assertTrue(all(r.explanation_source == "ai" for r in resp.routes))
        facts = explainer.seen[0]
        self.assertEqual(set(facts), {"label", "duration_min", "extra_min", "coverage_pct", "longest_gap_m",
                                      "longest_gap_note", "worst_window_score", "route_score",
                                      "open_places_count", "nearest_help_point"})


class PriorityTests(unittest.TestCase):
    def test_priorities_boost_chosen_factors_and_still_sum_to_one(self):
        out = apply_priorities(CFG["weights"], ["lighting"], CFG["priorities"]["boost"])
        self.assertAlmostEqual(sum(out.values()), 1.0)
        self.assertGreater(out["lighting"], CFG["weights"]["lighting"])
        self.assertLess(out["open_places"], CFG["weights"]["open_places"])

    def test_friendly_alias_and_unknown_priorities(self):
        a = apply_priorities(CFG["weights"], ["main_roads"], 1.5)
        b = apply_priorities(CFG["weights"], ["main_road"], 1.5)
        self.assertEqual(a, b)
        self.assertEqual(apply_priorities(CFG["weights"], ["nonsense"], 1.5),
                         {k: v / sum(CFG["weights"].values()) for k, v in CFG["weights"].items()})

    def test_priority_changes_the_segment_score(self):
        with tempfile.TemporaryDirectory() as d:
            plain = fakes.make_planner(Path(d)).plan(request()).routes[0].segments[0].score
            lit = fakes.make_planner(Path(d)).plan(request(priorities=["lighting"])).routes[0].segments[0].score
        self.assertNotEqual(plain, lit)


class HelperTests(unittest.TestCase):
    def test_bbox_of_pads_all_candidates(self):
        box = bbox_of([fakes.route_a(), fakes.route_b()], pad=0.001)
        self.assertAlmostEqual(box.south, 37.8029 - 0.001)
        self.assertAlmostEqual(box.north, 37.8060 + 0.001)
        self.assertAlmostEqual(box.west, -122.4484 - 0.001)
        self.assertAlmostEqual(box.east, -122.4400 + 0.001)

    def test_confidence_labels_follow_config(self):
        self.assertEqual(confidence_for(1.0, CFG), "high")
        self.assertEqual(confidence_for(0.8, CFG), "high")
        self.assertEqual(confidence_for(0.6, CFG), "low")
        self.assertEqual(confidence_for(0.3, CFG), "unknown")


if __name__ == "__main__":
    unittest.main()
