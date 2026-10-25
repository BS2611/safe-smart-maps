"""Regression tests from the shape of a REAL Bright Data response (observed 2026-10-24).

Fixture: tests/fixtures/brightdata_live_shape_sample.json (trimmed real records, labeled, no credentials).
Network is faked; these pin the real field names and hour formats we learned from the live call.
"""
import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from server.data import brightdata
from server.data.brightdata import BrightDataError, BrightDataPlacesProvider, normalize_record
from server.data.models import BoundingBox
from server.data.opening_hours import OpenStatus, evaluate_open_status, parse_weekly_hours

RECORDS = json.loads((Path(__file__).parent / "fixtures" / "brightdata_live_shape_sample.json").read_text())["records"]
FETCHED = datetime(2026, 10, 24, tzinfo=timezone.utc)
LA = ZoneInfo("America/Los_Angeles")
BOX = BoundingBox(37.797, -122.455, 37.809, -122.440)


class FakeResp:
    def __init__(self, status=200, text=""):
        self.status_code, self.text = status, text


class LiveShapeTests(unittest.TestCase):
    def test_every_real_record_normalizes(self):
        places = [normalize_record(r, FETCHED) for r in RECORDS]
        self.assertTrue(all(places))
        # the live API returns places beyond the box too; the provider's area filter handles that
        self.assertTrue(any(BOX.contains(p.lat, p.lng) for p in places))

    def test_narrow_nbsp_hours_parse_and_evaluate(self):
        p = normalize_record(next(r for r in RECORDS if r["name"] == "Home Plate"), FETCHED)
        sat = datetime(2026, 10, 24, 10, tzinfo=LA)  # Saturday 7am-3pm
        self.assertEqual(evaluate_open_status(p, sat), OpenStatus.OPEN)
        self.assertEqual(evaluate_open_status(p, sat.replace(hour=20)), OpenStatus.CLOSED)

    def test_shared_meridiem_and_dot_minutes(self):
        w, _ = parse_weekly_hours({"Monday": "5–10 PM", "Tuesday": "5:30–9:30 PM",
                                   "Wednesday": "12–8:30 PM", "Thursday": "5.00 am–6.30 pm",
                                   "Friday": "11–2 PM", "Saturday": "8 a.m.–10 p.m."})
        self.assertEqual(w[0], [(17 * 60, 22 * 60)])
        self.assertEqual(w[1], [(17 * 60 + 30, 21 * 60 + 30)])
        self.assertEqual(w[2], [(12 * 60, 20 * 60 + 30)])
        self.assertEqual(w[3], [(5 * 60, 18 * 60 + 30)])
        self.assertEqual(w[4], [(11 * 60, 14 * 60)])  # 11 PM-2 PM is impossible: read as 11 AM-2 PM
        self.assertEqual(w[5], [(8 * 60, 22 * 60)])

    def test_missing_hours_is_unknown(self):
        p = normalize_record(next(r for r in RECORDS if not r["open_hours"]), FETCHED)
        self.assertEqual(evaluate_open_status(p, datetime(2026, 10, 24, 20, tzinfo=LA)), OpenStatus.UNKNOWN)


class AsyncSnapshotTests(unittest.TestCase):
    def _run(self, gets, provider=None):
        env = {"BRIGHTDATA_API_KEY": "test-fixture-key-not-real"}
        post = FakeResp(202, json.dumps({"snapshot_id": "sd_test"}))
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(brightdata.httpx, "post", return_value=post), \
             mock.patch.object(brightdata.httpx, "get", side_effect=gets) as get, \
             mock.patch.object(brightdata.time, "sleep"):
            p = provider or BrightDataPlacesProvider(poll_interval_s=0)
            return p.get_places(BOX, FETCHED), get

    def test_202_polls_then_downloads(self):
        gets = [FakeResp(200, '{"status":"running"}'), FakeResp(200, '{"status":"ready"}'),
                FakeResp(200, json.dumps(RECORDS))]
        places, get = self._run(gets)
        self.assertEqual(len(places), sum(BOX.contains(r['lat'], r['lon']) for r in RECORDS))
        self.assertGreater(len(places), 0)
        self.assertTrue(get.call_args.args[0].endswith("/snapshot/sd_test"))

    def test_failed_snapshot_raises(self):
        with self.assertRaises(BrightDataError):
            self._run([FakeResp(200, '{"status":"failed"}')])

    def test_timeout_raises(self):
        with self.assertRaises(BrightDataError):
            self._run([FakeResp(200, '{"status":"running"}')] * 5,
                      BrightDataPlacesProvider(poll_interval_s=0, max_wait_s=-1))


if __name__ == "__main__":
    unittest.main()
