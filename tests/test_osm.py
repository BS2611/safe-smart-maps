"""OSM normalization and OverpassContextProvider WITHOUT any real network.

All OSM elements below are hand-written TEST FIXTURES shaped like Overpass `out tags geom center`
output. They test OUR code, not OSM data.
"""
import unittest
from datetime import datetime, timezone
from unittest import mock

import httpx

from server.data import osm
from server.data.context import ContextProvider
from server.data.models import BoundingBox
from server.data.osm import (OsmError, OverpassContextProvider, classify_highway, normalize_elements,
                             normalize_help_point, normalize_lit, normalize_way)

NOW = datetime(2026, 10, 24, 20, tzinfo=timezone.utc)
BOX = BoundingBox(37.797, -122.455, 37.809, -122.440)
GEOM = [{"lat": 37.80, "lon": -122.45}, {"lat": 37.801, "lon": -122.449}]


def way(tags, id=1, geometry=GEOM, **extra):
    return {"type": "way", "id": id, "tags": tags, "geometry": geometry, **extra}


def node(amenity, id=10, name=None, lat=37.8, lon=-122.45, **extra):
    tags = {"amenity": amenity, **({"name": name} if name else {})}
    return {"type": "node", "id": id, "lat": lat, "lon": lon, "tags": tags, **extra}


class RoadClassTests(unittest.TestCase):
    def test_common_highways(self):
        for raw, want in [("primary", "primary"), ("secondary", "secondary"), ("tertiary", "tertiary"),
                          ("residential", "residential"), ("service", "service"),
                          ("footway", "pedestrian"), ("primary_link", "primary"), (" Primary ", "primary")]:
            self.assertEqual(classify_highway(raw), want, raw)

    def test_missing_is_unknown(self):
        for raw in (None, "", "  ", 5):
            self.assertEqual(classify_highway(raw), "unknown")

    def test_unexpected_value_is_other(self):
        self.assertEqual(classify_highway("bus_guideway"), "other")

    def test_partial_or_malformed_features_are_skipped(self):
        for el in (None, "x", {}, {"type": "way"}, way({"name": "no highway"}), way({"highway": "primary"}, geometry=[]),
                   way({"highway": "primary"}, geometry=[GEOM[0]]),
                   way({"highway": "primary"}, geometry=[{"lat": "a", "lon": 1}, {"lat": None}]),
                   way({"highway": "primary"}, geometry=None), {"type": "node", "tags": {"highway": "primary"}}):
            self.assertIsNone(normalize_way(el, NOW), el)

    def test_way_keeps_matching_info(self):
        r = normalize_way(way({"highway": "secondary", "lit": "yes", "name": "Lyon St"}, id=7), NOW)
        self.assertEqual((r.road_class, r.lit, r.name, r.osm_id, r.raw_highway, r.source),
                         ("secondary", "yes", "Lyon St", 7, "secondary", "osm"))
        self.assertEqual(r.coordinates, ((37.80, -122.45), (37.801, -122.449)))


class LightingTests(unittest.TestCase):
    def test_yes_no(self):
        self.assertEqual(normalize_lit("yes"), "yes")
        self.assertEqual(normalize_lit("YES "), "yes")
        self.assertEqual(normalize_lit("no"), "no")

    def test_missing_is_unknown_not_unlit(self):
        self.assertEqual(normalize_lit(None), "unknown")
        self.assertEqual(normalize_way(way({"highway": "residential"}), NOW).lit, "unknown")

    def test_unexpected_value_is_unknown(self):
        for raw in ("automatic", "limited", "maybe", "", 1, True):
            self.assertEqual(normalize_lit(raw), "unknown", raw)


class HelpPointTests(unittest.TestCase):
    def test_three_categories(self):
        for kind in ("police", "hospital", "fire_station"):
            hp = normalize_help_point(node(kind, name="Some Place"), NOW)
            self.assertEqual((hp.type, hp.lat, hp.lng, hp.name, hp.source), (kind, 37.8, -122.45, "Some Place", "osm"))

    def test_way_uses_center(self):
        el = {"type": "way", "id": 3, "center": {"lat": 37.805, "lon": -122.44}, "tags": {"amenity": "hospital"}}
        hp = normalize_help_point(el, NOW)
        self.assertEqual((hp.lat, hp.lng, hp.name), (37.805, -122.44, None))

    def test_missing_coordinates(self):
        for el in ({"type": "node", "id": 1, "tags": {"amenity": "police"}},
                   {"type": "way", "id": 1, "tags": {"amenity": "police"}},
                   node("police", lat=None), node("police", lon="x")):
            self.assertIsNone(normalize_help_point(el, NOW))

    def test_unrelated_pois_filtered(self):
        for kind in ("cafe", "school", "pharmacy", "clinic"):
            self.assertIsNone(normalize_help_point(node(kind), NOW))
        self.assertIsNone(normalize_help_point({"type": "node", "lat": 1, "lon": 1, "tags": {}}, NOW))

    def test_extra_fields_ignored(self):
        hp = normalize_help_point(node("police", weird={"a": 1}, version=3), NOW)
        self.assertEqual(hp.type, "police")
        r = normalize_way(way({"highway": "primary", "surface": "asphalt", "maxspeed": "25 mph"}, bounds={}), NOW)
        self.assertEqual(r.road_class, "primary")


class NormalizeElementsTests(unittest.TestCase):
    def test_dedupe_by_osm_id_and_node_plus_building(self):
        ctx = normalize_elements([
            way({"highway": "primary"}, id=1), way({"highway": "primary"}, id=1),
            node("hospital", id=5, name="General"),
            {"type": "way", "id": 6, "center": {"lat": 37.8001, "lon": -122.4501},
             "tags": {"amenity": "hospital", "name": "General"}},
            node("hospital", id=7, name="Other", lat=37.81),
        ], NOW)
        self.assertEqual(len(ctx.roads), 1)
        self.assertEqual([h.name for h in ctx.help_points], ["General", "Other"])

    def test_non_list_is_empty(self):
        for bad in (None, {}, "x"):
            ctx = normalize_elements(bad, NOW)
            self.assertEqual((ctx.roads, ctx.help_points), ([], []))


class FakeResp:
    def __init__(self, status=200, payload=None, bad_json=False):
        self.status_code, self._p, self._bad = status, payload, bad_json

    def json(self):
        if self._bad:
            raise ValueError("bad")
        return self._p


class ProviderTests(unittest.TestCase):
    def run_with(self, resp=None, exc=None):
        post = mock.Mock(return_value=resp, side_effect=exc)
        with mock.patch.object(osm.httpx, "post", post):
            return OverpassContextProvider(url="https://overpass.test/api").get_area_context(BOX), post

    def test_success(self):
        ctx, post = self.run_with(FakeResp(payload={"elements": [
            way({"highway": "primary", "lit": "yes"}), way({"highway": "service", "lit": "no"}, id=2),
            node("police", name="SFPD")]}))
        self.assertEqual([(r.road_class, r.lit) for r in ctx.roads], [("primary", "yes"), ("service", "no")])
        self.assertEqual(ctx.help_points[0].type, "police")
        self.assertEqual(ctx.fetched_at.tzinfo, timezone.utc)
        self.assertEqual(post.call_count, 1)
        query = post.call_args.kwargs["data"]["data"]
        self.assertIn("37.797,-122.455,37.809,-122.44", query)
        self.assertIn("police|hospital|fire_station", query)

    def test_is_a_context_provider(self):
        self.assertIsInstance(OverpassContextProvider(), ContextProvider)

    def test_empty(self):
        ctx, _ = self.run_with(FakeResp(payload={"elements": []}))
        self.assertEqual((ctx.roads, ctx.help_points), ([], []))

    def test_failures_raise_osm_error(self):
        for kwargs in ({"resp": FakeResp(status=429)}, {"resp": FakeResp(status=504)},
                       {"resp": FakeResp(bad_json=True)}, {"resp": FakeResp(payload={"nope": 1})},
                       {"resp": FakeResp(payload={"elements": [], "remark": "runtime error: Query timed out"})},
                       {"exc": httpx.ConnectTimeout("t")}):
            with self.assertRaises(OsmError, msg=kwargs):
                self.run_with(**kwargs)


if __name__ == "__main__":
    unittest.main()
