"""Mapbox walking-route provider WITHOUT any real network.

Every Mapbox answer below is a hand-written TEST FIXTURE shaped like Directions v5 output
(tests/fixtures/mapbox_directions_sample.json plus small inline variants). They test OUR
normalization, not Mapbox. The one real call lives in scripts/mapbox_smoke.py.
"""
import copy
import dataclasses
import json
import unittest
from pathlib import Path
from unittest import mock

import httpx

from server.data import mapbox
from server.data.mapbox import (
    MapboxError,
    MapboxWalkingProvider,
    RouteCandidate,
    check_point,
    parse_directions,
)

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "mapbox_directions_sample.json").read_text(encoding="utf-8"))
FAKE_TOKEN = "pk.test-token-not-real-0123456789"
ORIGIN = (-122.4484, 37.8029)  # (lng, lat) Palace of Fine Arts
DEST = (-122.4013, 37.7894)    # (lng, lat) Montgomery BART


def fixture() -> dict:
    return copy.deepcopy(FIXTURE)


def route(coords=None, distance=1000.0, duration=700.0, **extra) -> dict:
    coords = coords if coords is not None else [[-122.45, 37.80], [-122.44, 37.81]]
    return {"distance": distance, "duration": duration,
            "geometry": {"type": "LineString", "coordinates": coords}, **extra}


class FakeTransport:
    """httpx transport that records requests and answers with a canned response or exception."""

    def __init__(self, answer):
        self.answer = answer
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def provider(answer, token=FAKE_TOKEN) -> tuple[MapboxWalkingProvider, FakeTransport]:
    transport = FakeTransport(answer)
    client = httpx.Client(transport=httpx.MockTransport(transport))
    return MapboxWalkingProvider(token=token, client=client), transport


def ok(payload) -> httpx.Response:
    return httpx.Response(200, json=payload)


class SuccessTests(unittest.TestCase):
    def test_fixture_normalizes_into_project_routes(self):
        routes = parse_directions(fixture())
        first = routes[0]
        self.assertEqual(first.id, "mapbox-0")
        self.assertEqual(first.provider, "mapbox")
        self.assertEqual(first.distance_m, 5120.7)
        self.assertEqual(first.duration_s, 3650.4)
        self.assertEqual(len(first.coordinates), 7)
        self.assertEqual(first.coordinates[0], (-122.4484, 37.8029))
        self.assertEqual(first.coordinates[-1], (-122.4013, 37.7894))

    def test_alternatives_are_all_kept_in_mapbox_order(self):
        routes = parse_directions(fixture())
        self.assertEqual([r.id for r in routes], ["mapbox-0", "mapbox-1", "mapbox-2"])
        self.assertEqual([r.distance_m for r in routes], [5120.7, 5310.2, 5605.5])
        self.assertEqual([len(r.coordinates) for r in routes], [7, 6, 7])

    def test_single_route_response_works(self):
        payload = fixture()
        payload["routes"] = payload["routes"][:1]
        routes = parse_directions(payload)
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0].id, "mapbox-0")

    def test_provider_returns_the_same_routes_as_the_parser(self):
        p, transport = provider(ok(fixture()))
        routes = p.get_walking_routes(ORIGIN, DEST)
        self.assertEqual(routes, parse_directions(fixture()))
        self.assertEqual(len(transport.requests), 1)

    def test_route_is_immutable_and_has_only_the_contract_fields(self):
        r = parse_directions(fixture())[0]
        self.assertEqual([f.name for f in dataclasses.fields(r)],
                         ["id", "provider", "coordinates", "distance_m", "duration_s"])
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r.distance_m = 1.0  # type: ignore[misc]


class CoordinateOrderTests(unittest.TestCase):
    def test_coordinates_stay_longitude_then_latitude(self):
        for lng, lat in parse_directions(fixture())[0].coordinates:
            self.assertTrue(-123 < lng < -122, lng)   # San Francisco longitude comes first
            self.assertTrue(37 < lat < 38, lat)

    def test_as_lat_lng_swaps_for_the_segmenter(self):
        r = parse_directions(fixture())[0]
        self.assertEqual(r.as_lat_lng()[0], (37.8029, -122.4484))
        self.assertEqual(len(r.as_lat_lng()), len(r.coordinates))
        self.assertEqual(r.coordinates[0], (-122.4484, 37.8029))  # the original is untouched

    def test_request_url_sends_origin_then_destination_as_lng_lat(self):
        p, transport = provider(ok(fixture()))
        p.get_walking_routes(ORIGIN, DEST)
        self.assertTrue(
            str(transport.requests[0].url.path).endswith("/walking/-122.448400,37.802900;-122.401300,37.789400"),
            transport.requests[0].url.path)

    def test_swapped_lat_lng_input_is_rejected_not_silently_used(self):
        p, transport = provider(ok(fixture()))
        with self.assertRaises(ValueError):
            p.get_walking_routes((37.8029, -122.4484), DEST)   # (lat, lng) by mistake
        self.assertEqual(transport.requests, [])

    def test_response_point_with_swapped_order_is_dropped(self):
        payload = {"routes": [route(coords=[[37.80, -122.45], [37.81, -122.44]])]}  # lat first
        with self.assertRaises(MapboxError) as cm:
            parse_directions(payload)
        self.assertEqual(cm.exception.kind, "failed")

    def test_elevation_third_value_is_ignored(self):
        payload = {"routes": [route(coords=[[-122.45, 37.80, 12.0], [-122.44, 37.81, 14.5]])]}
        self.assertEqual(parse_directions(payload)[0].coordinates, [(-122.45, 37.80), (-122.44, 37.81)])


class UnitsTests(unittest.TestCase):
    def test_distance_is_meters_and_duration_is_seconds_with_no_conversion(self):
        r = parse_directions({"routes": [route(distance=1234.5, duration=987.6)]})[0]
        self.assertEqual(r.distance_m, 1234.5)
        self.assertEqual(r.duration_s, 987.6)

    def test_integers_become_floats(self):
        r = parse_directions({"routes": [route(distance=1000, duration=700)]})[0]
        self.assertIsInstance(r.distance_m, float)
        self.assertIsInstance(r.duration_s, float)

    def test_walking_speed_in_fixture_is_plausible(self):
        for r in parse_directions(fixture()):
            self.assertTrue(0.8 < r.distance_m / r.duration_s < 2.0, r.id)  # m/s, a person walking


class EmptyAndMalformedTests(unittest.TestCase):
    def test_empty_routes_is_a_clear_empty_error(self):
        with self.assertRaises(MapboxError) as cm:
            parse_directions({"code": "NoRoute", "routes": []})
        self.assertEqual(cm.exception.kind, "empty")
        self.assertIn("no walking route", str(cm.exception))
        self.assertIn("NoRoute", str(cm.exception))

    def test_empty_routes_through_the_provider(self):
        p, _ = provider(ok({"code": "NoRoute", "routes": []}))
        with self.assertRaises(MapboxError) as cm:
            p.get_walking_routes(ORIGIN, DEST)
        self.assertEqual(cm.exception.kind, "empty")

    def test_odd_code_value_is_not_echoed(self):
        with self.assertRaises(MapboxError) as cm:
            parse_directions({"code": "bad code <script>", "routes": []})
        self.assertNotIn("script", str(cm.exception))

    def test_unusable_geometry_variants_are_rejected(self):
        bad_geometries = {
            "geometry missing": {"distance": 1000.0, "duration": 700.0},
            "geometry not an object": {"distance": 1000.0, "duration": 700.0, "geometry": "abc123"},
            "coordinates missing": {"distance": 1000.0, "duration": 700.0, "geometry": {"type": "LineString"}},
            "coordinates empty": route(coords=[]),
            "single point": route(coords=[[-122.45, 37.80]]),
            "strings instead of numbers": route(coords=[["-122.45", "37.80"], ["-122.44", "37.81"]]),
            "pair too short": route(coords=[[-122.45], [-122.44, 37.81]]),
            "point not a list": route(coords=[{"lng": -122.45, "lat": 37.80}, [-122.44, 37.81]]),
            "null point": route(coords=[None, [-122.44, 37.81]]),
            "longitude out of range": route(coords=[[-222.45, 37.80], [-122.44, 37.81]]),
            "latitude out of range": route(coords=[[-122.45, 137.80], [-122.44, 37.81]]),
            "NaN": route(coords=[[float("nan"), 37.80], [-122.44, 37.81]]),
            "boolean": route(coords=[[True, 37.80], [-122.44, 37.81]]),
        }
        for name, bad in bad_geometries.items():
            with self.subTest(name):
                with self.assertRaises(MapboxError) as cm:
                    parse_directions({"routes": [bad]})
                self.assertEqual(cm.exception.kind, "failed")
                self.assertIn("no usable route geometry", str(cm.exception))

    def test_bad_distance_or_duration_is_rejected(self):
        for name, bad in {"zero distance": route(distance=0), "negative duration": route(duration=-5),
                          "string distance": route(distance="1000"), "missing duration":
                          {"distance": 1000.0, "geometry": route()["geometry"]},
                          "infinite": route(distance=float("inf")), "null": route(duration=None)}.items():
            with self.subTest(name):
                with self.assertRaises(MapboxError):
                    parse_directions({"routes": [bad]})

    def test_one_bad_route_is_dropped_and_ids_do_not_shift(self):
        payload = fixture()
        payload["routes"][1] = {"distance": 5310.2, "duration": 3790.0}   # no geometry
        routes = parse_directions(payload)
        self.assertEqual([r.id for r in routes], ["mapbox-0", "mapbox-2"])

    def test_unexpected_response_shapes(self):
        for name, payload in {"list": [], "string": "nope", "none": None, "no routes key": {"code": "Ok"},
                              "routes not a list": {"routes": {"a": 1}}}.items():
            with self.subTest(name):
                with self.assertRaises(MapboxError) as cm:
                    parse_directions(payload)
                self.assertEqual(cm.exception.kind, "failed")

    def test_non_object_route_entries_are_dropped(self):
        routes = parse_directions({"routes": ["junk", None, 5, route()]})
        self.assertEqual([r.id for r in routes], ["mapbox-3"])


class ExtraVendorFieldsTests(unittest.TestCase):
    def test_unknown_fields_everywhere_do_not_break_normalization(self):
        payload = fixture()
        payload["brand_new_top_level"] = {"x": 1}
        payload["routes"][0]["brand_new_route_field"] = [1, 2]
        payload["routes"][0]["geometry"]["crs"] = "EPSG:4326"
        routes = parse_directions(payload)
        self.assertEqual(len(routes), 3)
        self.assertEqual(routes, parse_directions(fixture()))

    def test_vendor_fields_do_not_leak_into_the_route(self):
        self.assertFalse(any(hasattr(parse_directions(fixture())[0], f)
                             for f in ("legs", "weight", "weight_name", "uuid", "waypoints")))


class TokenTests(unittest.TestCase):
    def test_missing_token_is_explicit_and_makes_no_request(self):
        transport = FakeTransport(ok(fixture()))
        client = httpx.Client(transport=httpx.MockTransport(transport))
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(MapboxError) as cm:
                MapboxWalkingProvider(client=client).get_walking_routes(ORIGIN, DEST)
        self.assertEqual(cm.exception.kind, "not_configured")
        self.assertIn("MAPBOX_TOKEN is not set", str(cm.exception))
        self.assertEqual(transport.requests, [])

    def test_blank_token_counts_as_missing(self):
        for blank in ("", "   "):
            with self.subTest(repr(blank)), mock.patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(MapboxError) as cm:
                    MapboxWalkingProvider(token=blank).get_walking_routes(ORIGIN, DEST)
                self.assertEqual(cm.exception.kind, "not_configured")

    def test_token_is_read_from_the_environment_at_call_time(self):
        transport = FakeTransport(ok(fixture()))
        p = MapboxWalkingProvider(client=httpx.Client(transport=httpx.MockTransport(transport)))
        with mock.patch.dict("os.environ", {"MAPBOX_TOKEN": FAKE_TOKEN}, clear=True):
            p.get_walking_routes(ORIGIN, DEST)
        self.assertEqual(transport.requests[0].url.params["access_token"], FAKE_TOKEN)

    def test_explicit_token_wins_over_the_environment(self):
        p, transport = provider(ok(fixture()), token="pk.explicit")
        with mock.patch.dict("os.environ", {"MAPBOX_TOKEN": FAKE_TOKEN}, clear=True):
            p.get_walking_routes(ORIGIN, DEST)
        self.assertEqual(transport.requests[0].url.params["access_token"], "pk.explicit")


class FailureTests(unittest.TestCase):
    def assert_clean_error(self, answer, kind, contains=""):
        p, _ = provider(answer)
        with self.assertRaises(MapboxError) as cm:
            p.get_walking_routes(ORIGIN, DEST)
        message = str(cm.exception)
        self.assertEqual(cm.exception.kind, kind, message)
        self.assertIn(contains, message)
        for secret in (FAKE_TOKEN, "access_token", "api.mapbox.com", "-122.4484", "37.8029"):
            self.assertNotIn(secret, message)

    def test_http_error_statuses(self):
        for status in (401, 403, 404, 422, 429, 500, 502, 503):
            with self.subTest(status):
                self.assert_clean_error(httpx.Response(status, json={"message": "Not Authorized - Invalid Token"}),
                                        "failed", f"HTTP {status}")

    def test_timeout(self):
        self.assert_clean_error(httpx.ReadTimeout("slow"), "timeout", "timed out")
        self.assert_clean_error(httpx.ConnectTimeout("slow"), "timeout", "timed out")

    def test_connection_failure_message_has_class_only(self):
        # httpx puts the full URL (with the token) into str(error); we must not repeat it.
        error = httpx.ConnectError(f"cannot connect to https://api.mapbox.com/x?access_token={FAKE_TOKEN}")
        self.assert_clean_error(error, "failed", "ConnectError")

    def test_non_json_body(self):
        self.assert_clean_error(httpx.Response(200, text="<html>maintenance</html>"), "failed", "not valid JSON")

    def test_no_exception_chain_leaks_the_url(self):
        p, _ = provider(httpx.ConnectError(f"https://x/?access_token={FAKE_TOKEN}"))
        with self.assertRaises(MapboxError) as cm:
            p.get_walking_routes(ORIGIN, DEST)
        self.assertIsNone(cm.exception.__cause__)
        self.assertTrue(cm.exception.__suppress_context__)

    def test_error_is_a_runtime_error_with_a_source_prefix(self):
        self.assertTrue(issubclass(MapboxError, RuntimeError))
        self.assertTrue(str(MapboxError("x")).startswith("mapbox: "))


class RequestShapeTests(unittest.TestCase):
    def setUp(self):
        p, self.transport = provider(ok(fixture()))
        p.get_walking_routes(ORIGIN, DEST)
        self.request = self.transport.requests[0]

    def test_uses_the_walking_profile(self):
        self.assertIn("/directions/v5/mapbox/walking/", str(self.request.url))

    def test_asks_for_alternatives_and_full_geojson_geometry(self):
        params = self.request.url.params
        self.assertEqual(params["alternatives"], "true")
        self.assertEqual(params["geometries"], "geojson")
        self.assertEqual(params["overview"], "full")
        self.assertEqual(params["steps"], "false")

    def test_is_a_single_get_request(self):
        self.assertEqual(self.request.method, "GET")
        self.assertEqual(len(self.transport.requests), 1)

    def test_timeout_is_passed_to_the_client(self):
        client = mock.Mock()
        client.get.return_value = ok(fixture())
        MapboxWalkingProvider(token=FAKE_TOKEN, timeout_s=7.5, client=client).get_walking_routes(ORIGIN, DEST)
        self.assertEqual(client.get.call_args.kwargs["timeout"], 7.5)


class InputValidationTests(unittest.TestCase):
    def test_bad_points_raise_value_error_before_any_request(self):
        bad = {"lat/lng swapped": (37.8029, -122.4484), "latitude too big": (-122.4, 91.0),
               "longitude too big": (181.0, 37.0), "three values": (1.0, 2.0, 3.0), "one value": (1.0,),
               "strings": ("-122.4", "37.8"), "None": None, "NaN": (float("nan"), 37.0),
               "bool": (True, 37.0), "number": 5}
        for name, point in bad.items():
            for which in ("origin", "dest"):
                with self.subTest(f"{name} as {which}"):
                    p, transport = provider(ok(fixture()))
                    args = (point, DEST) if which == "origin" else (ORIGIN, point)
                    with self.assertRaises(ValueError):
                        p.get_walking_routes(*args)
                    self.assertEqual(transport.requests, [])

    def test_check_point_accepts_lists_and_boundaries(self):
        self.assertEqual(check_point([-180, 90], "p"), (-180.0, 90.0))
        self.assertEqual(check_point((180, -90), "p"), (180.0, -90.0))

    def test_module_exposes_the_documented_names(self):
        for name in ("RouteCandidate", "MapboxWalkingProvider", "MapboxError", "parse_directions", "DIRECTIONS_URL"):
            self.assertTrue(hasattr(mapbox, name), name)
        self.assertIsInstance(parse_directions(fixture())[0], RouteCandidate)


class WaypointTests(unittest.TestCase):
    VIA = (-122.4400, 37.8000)

    def test_waypoint_is_placed_between_origin_and_destination(self):
        p, transport = provider(ok(fixture()))
        p.get_walking_routes(ORIGIN, DEST, waypoints=[self.VIA])
        self.assertTrue(str(transport.requests[0].url.path).endswith(
            "/walking/-122.448400,37.802900;-122.440000,37.800000;-122.401300,37.789400"))

    def test_alternatives_are_turned_off_when_a_waypoint_is_forced(self):
        p, transport = provider(ok(fixture()))
        p.get_walking_routes(ORIGIN, DEST, waypoints=[self.VIA])
        self.assertEqual(transport.requests[0].url.params["alternatives"], "false")

    def test_no_waypoints_keeps_alternatives_on(self):
        p, transport = provider(ok(fixture()))
        p.get_walking_routes(ORIGIN, DEST, waypoints=[])
        self.assertEqual(transport.requests[0].url.params["alternatives"], "true")

    def test_bad_waypoint_raises_before_any_request(self):
        p, transport = provider(ok(fixture()))
        for bad in ((37.8, -122.44), None, (1.0,)):
            with self.subTest(bad), self.assertRaises(ValueError):
                p.get_walking_routes(ORIGIN, DEST, waypoints=[bad])
        self.assertEqual(transport.requests, [])


if __name__ == "__main__":
    unittest.main()
