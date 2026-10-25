"""BrightDataPlacesProvider behavior WITHOUT any real network.

httpx.post is replaced by a fake returning hand-written TEST FIXTURE responses. This tests OUR
code (filtering, dedupe, error handling). It does NOT verify Bright Data itself: the real API,
auth, dataset id and open_hours shape remain unverified until a key is configured.
"""
import json
import os
import unittest
from unittest import mock

import httpx

from server.data import brightdata
from server.data.brightdata import BrightDataError, BrightDataPlacesProvider
from server.data.models import BoundingBox, Place
from server.data.places import PlacesProvider
from datetime import datetime, timezone

BOX = BoundingBox(37.70, -122.50, 37.80, -122.40)
NOW = datetime(2026, 10, 24, 20, tzinfo=timezone.utc)
FAKE_KEY = "test-fixture-key-not-real"


def rec(name, lat=37.75, lng=-122.45, **kw):
    return {"name": name, "latitude": lat, "longitude": lng, "category": "Cafe", **kw}


class FakeResp:
    def __init__(self, status=200, text=""):
        self.status_code, self.text = status, text


def run(resp=None, exc=None, env=None, provider=None):
    """Call get_places with a fake httpx.post. Returns (result_or_exception, post_mock)."""
    env = {"BRIGHTDATA_API_KEY": FAKE_KEY} if env is None else env
    with mock.patch.dict(os.environ, env, clear=True), \
         mock.patch.object(brightdata.httpx, "post", side_effect=exc, return_value=resp) as post:
        return (provider or BrightDataPlacesProvider()).get_places(BOX, NOW), post


class ConfigFailureTests(unittest.TestCase):
    def test_missing_key_raises_before_any_request(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(brightdata.httpx, "post") as post:
            with self.assertRaises(BrightDataError) as cm:
                BrightDataPlacesProvider().get_places(BOX, NOW)
        post.assert_not_called()
        self.assertIn("BRIGHTDATA_API_KEY", str(cm.exception))

    def test_empty_key_treated_as_missing(self):
        with mock.patch.dict(os.environ, {"BRIGHTDATA_API_KEY": ""}, clear=True), \
             mock.patch.object(brightdata.httpx, "post") as post:
            with self.assertRaises(BrightDataError):
                BrightDataPlacesProvider().get_places(BOX, NOW)
        post.assert_not_called()


class RequestShapeTests(unittest.TestCase):
    def test_blank_dataset_id_in_env_falls_back_to_default(self):
        # .env.example ships `BRIGHTDATA_PLACES_DATASET_ID=` (blank); real API rejected "" with HTTP 400.
        _, post = run(FakeResp(200, "[]"), env={"BRIGHTDATA_API_KEY": FAKE_KEY, "BRIGHTDATA_PLACES_DATASET_ID": ""})
        self.assertEqual(post.call_args.kwargs["params"]["dataset_id"], brightdata.DEFAULT_DATASET_ID)

    def test_request_built_from_area_and_env(self):
        _, post = run(FakeResp(200, "[]"), env={"BRIGHTDATA_API_KEY": FAKE_KEY,
                                               "BRIGHTDATA_PLACES_DATASET_ID": "gd_test"})
        kw = post.call_args.kwargs
        self.assertEqual(post.call_args.args[0], brightdata.SCRAPE_URL)
        self.assertEqual(kw["params"]["dataset_id"], "gd_test")
        self.assertEqual(kw["headers"], {"Authorization": f"Bearer {FAKE_KEY}"})
        inputs = kw["json"]["input"]
        self.assertEqual([i["keyword"] for i in inputs], list(brightdata.DEFAULT_KEYWORDS))
        self.assertAlmostEqual(inputs[0]["lat"], 37.75)
        self.assertAlmostEqual(inputs[0]["long"], -122.45)

    def test_default_dataset_id(self):
        _, post = run(FakeResp(200, "[]"))
        self.assertEqual(post.call_args.kwargs["params"]["dataset_id"], brightdata.DEFAULT_DATASET_ID)

    def test_custom_keywords(self):
        _, post = run(FakeResp(200, "[]"), provider=BrightDataPlacesProvider(keywords=("pharmacy",)))
        self.assertEqual(len(post.call_args.kwargs["json"]["input"]), 1)


class UpstreamFailureTests(unittest.TestCase):
    def assert_error(self, resp=None, exc=None, contains=""):
        with self.assertRaises(BrightDataError) as cm:
            run(resp, exc)
        self.assertIn(contains, str(cm.exception))
        self.assertNotIn(FAKE_KEY, str(cm.exception))

    def test_http_errors(self):
        for code in (400, 401, 403, 429, 500, 503):
            self.assert_error(FakeResp(code, "boom"), contains=str(code))

    def test_202_async(self):
        self.assert_error(FakeResp(202, "{}"), contains="202")

    def test_transport_errors_wrapped(self):
        for exc in (httpx.ConnectError("x"), httpx.ReadTimeout("x"), httpx.HTTPError("x")):
            self.assert_error(exc=exc, contains=type(exc).__name__)

    def test_invalid_json_body(self):
        self.assert_error(FakeResp(200, "<html>nope</html>"), contains="valid JSON")

    def test_error_message_never_contains_key_or_body(self):
        with self.assertRaises(BrightDataError) as cm:
            run(FakeResp(500, f"secret body {FAKE_KEY}"))
        self.assertNotIn("secret body", str(cm.exception))
        self.assertNotIn(FAKE_KEY, str(cm.exception))


class GracefulDegradationTests(unittest.TestCase):
    def places(self, records):
        return run(FakeResp(200, json.dumps(records)))[0]

    def test_empty_results(self):
        self.assertEqual(self.places([]), [])
        self.assertEqual(run(FakeResp(200, ""))[0], [])

    def test_returns_place_objects(self):
        out = self.places([rec("A", place_id="1")])
        self.assertIsInstance(out[0], Place)
        self.assertEqual(out[0].source, "brightdata")
        self.assertEqual(out[0].fetched_at.tzinfo, timezone.utc)

    def test_bad_records_skipped_good_kept(self):
        out = self.places([rec("Good", place_id="1"), {"name": "no coords"}, None, "junk", 5,
                           {"error": "x", **rec("Err")}, rec("", place_id="2"),
                           rec("Nan", lat="nan", place_id="3"), rec("Good2", place_id="4")])
        self.assertEqual([p.name for p in out], ["Good", "Good2"])

    def test_outside_box_filtered_edges_kept(self):
        out = self.places([rec("In", place_id="1"), rec("Out", lat=40.0, place_id="2"),
                           rec("Edge", lat=37.80, lng=-122.40, place_id="3"),
                           rec("JustOut", lat=37.8001, place_id="4")])
        self.assertEqual({p.name for p in out}, {"In", "Edge"})

    def test_dedupe_by_place_id_last_wins(self):
        out = self.places([rec("First", place_id="1"), rec("Second", place_id="1")])
        self.assertEqual([p.name for p in out], ["Second"])

    def test_dedupe_without_place_id_by_name_and_coords(self):
        out = self.places([rec("Same"), rec("Same"), rec("Same", lat=37.76)])
        self.assertEqual(len(out), 2)

    def test_different_ids_same_spot_kept(self):
        self.assertEqual(len(self.places([rec("A", place_id="1"), rec("A", place_id="2")])), 2)

    def test_ndjson_body(self):
        out = run(FakeResp(200, json.dumps(rec("A", place_id="1")) + "\n" + json.dumps(rec("B", place_id="2"))))[0]
        self.assertEqual(len(out), 2)

    def test_all_records_bad_gives_empty_list_not_error(self):
        self.assertEqual(self.places([{"name": "x"}, {"error": "y"}]), [])

    def test_malformed_hours_keep_place_with_unknown_hours(self):
        out = self.places([rec("A", place_id="1", open_hours="???")])
        self.assertIsNone(out[0].weekly_hours)


class InterfaceTests(unittest.TestCase):
    def test_is_a_places_provider(self):
        self.assertIsInstance(BrightDataPlacesProvider(), PlacesProvider)

    def test_abstract_base_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            PlacesProvider()  # type: ignore[abstract]


if __name__ == "__main__":
    unittest.main()
