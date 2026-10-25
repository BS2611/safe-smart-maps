"""Cache + prefetch tests. Upstream is a labeled FAKE provider; no network, no Bright Data."""
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from server.data.brightdata import BrightDataError
from server.data.cache import (CachedPlacesProvider, CacheEntry, FilePlacesCache, place_from_json,
                               place_to_json)
from server.data.models import BoundingBox, Place
from server.data.places import PlacesProvider
from server.main import app
from server.services.prefetch import cache_status, start_prefetch

AREA = BoundingBox(south=37.797, west=-122.455, north=37.809, east=-122.440)
NOW = datetime(2026, 10, 24, 20, 0, tzinfo=timezone.utc)


def make_place(name="Fixture Cafe", lat=37.80, lng=-122.45, fetched_at=NOW, hours=True):
    return Place(name=name, lat=lat, lng=lng, category="cafe", source="brightdata",
                 fetched_at=fetched_at, weekly_hours={0: [(540, 1020)], 5: [(1080, 1560)], 6: []} if hours else None,
                 is_24h=False if hours else None, place_id=name, raw_category="Cafe")


class FakeUpstream(PlacesProvider):
    """FIXTURE: stands in for Bright Data."""
    def __init__(self, places=None, error=None, gate=None):
        self.places, self.error, self.gate, self.calls = places or [], error, gate, 0

    def get_places(self, area, time):
        self.calls += 1
        if self.gate:
            self.gate.wait(5)
        if self.error:
            raise self.error
        return list(self.places)


class CacheCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def provider(self, upstream, ttl=3600):
        return CachedPlacesProvider(upstream, FilePlacesCache(self.dir), "brightdata", ttl)


class RoundTripTests(unittest.TestCase):
    def test_place_json_round_trip(self):
        for p in (make_place(), make_place(hours=False)):
            self.assertEqual(place_from_json(json.loads(json.dumps(place_to_json(p)))), p)


class LookupTests(CacheCase):
    def test_miss_returns_empty_and_never_calls_upstream(self):
        up = FakeUpstream([make_place()])
        c = self.provider(up)
        look = c.lookup(AREA)
        self.assertEqual((look.status, look.places, look.fetched_at), ("miss", [], None))
        self.assertEqual(c.get_places(AREA, NOW), [])
        self.assertEqual(up.calls, 0)

    def test_fresh_after_refresh_and_survives_restart(self):
        c = self.provider(FakeUpstream([make_place(), make_place("Outside", lat=38.5)]))
        self.assertEqual(c.refresh(AREA), 2)
        c2 = self.provider(FakeUpstream())           # new object = server restart
        look = c2.lookup(AREA)
        self.assertEqual(look.status, "fresh")
        self.assertEqual([p.name for p in look.places], ["Fixture Cafe"])   # filtered to area
        self.assertEqual(c2.upstream.calls, 0)

    def test_stale_is_served_with_original_data_time(self):
        c = self.provider(FakeUpstream([make_place()]), ttl=60)
        c.refresh(AREA)
        look = c.lookup(AREA, datetime.now(timezone.utc) + timedelta(seconds=61))
        self.assertEqual(look.status, "stale")
        self.assertEqual(len(look.places), 1)
        self.assertIsNotNone(look.fetched_at)

    def test_smaller_area_uses_covering_entry(self):
        c = self.provider(FakeUpstream([make_place()]))
        c.refresh(AREA)
        inner = BoundingBox(37.799, -122.452, 37.803, -122.445)
        self.assertEqual(c.lookup(inner).status, "fresh")
        outer = BoundingBox(37.0, -123.0, 38.0, -122.0)
        self.assertEqual(c.lookup(outer).status, "miss")

    def test_corrupt_file_is_a_miss(self):
        c = self.provider(FakeUpstream([make_place()]))
        c.refresh(AREA)
        for f in self.dir.glob("*.json"):
            f.write_text("{not json")
        self.assertEqual(c.lookup(AREA).status, "miss")


class RefreshTests(CacheCase):
    def test_failure_keeps_old_entry_and_records_error(self):
        c = self.provider(FakeUpstream([make_place()]))
        c.refresh(AREA)
        c.upstream.error = BrightDataError("Bright Data returned HTTP 500")
        with self.assertRaises(BrightDataError):
            c.refresh(AREA)
        self.assertEqual(len(c.lookup(AREA).places), 1)
        self.assertIn("HTTP 500", next(iter(c.last_error.values())))

    def test_empty_result_does_not_replace_good_entry(self):
        c = self.provider(FakeUpstream([make_place()]))
        c.refresh(AREA)
        c.upstream.places = []
        self.assertEqual(c.refresh(AREA), 0)
        self.assertEqual(len(c.lookup(AREA).places), 1)
        self.assertTrue(c.last_error)

    def test_empty_result_stored_when_nothing_cached(self):
        c = self.provider(FakeUpstream([]))
        c.refresh(AREA)
        self.assertEqual(c.lookup(AREA).status, "fresh")

    def test_background_refresh_is_single_flight(self):
        gate = threading.Event()
        up = FakeUpstream([make_place()], gate=gate)
        c = self.provider(up)
        self.assertTrue(c.request_refresh(AREA))
        self.assertTrue(c.lookup(AREA).refreshing)
        self.assertFalse(c.request_refresh(AREA))       # already running
        gate.set()
        for t in threading.enumerate():
            if t.name == "places-refresh":
                t.join(5)
        self.assertEqual(up.calls, 1)
        self.assertEqual(c.lookup(AREA).status, "fresh")
        self.assertFalse(c.lookup(AREA).refreshing)

    def test_no_temp_files_left(self):
        self.provider(FakeUpstream([make_place()])).refresh(AREA)
        self.assertEqual([f.suffix for f in self.dir.iterdir()], [".json"])


class PrefetchTests(CacheCase):
    def test_prefetch_only_for_missing_or_stale(self):
        up = FakeUpstream([make_place()])
        c = self.provider(up, ttl=3600)
        areas = {"demo": AREA}
        self.assertEqual(start_prefetch(c, areas), ["demo"])
        for t in threading.enumerate():
            if t.name == "places-refresh":
                t.join(5)
        self.assertEqual(start_prefetch(c, areas), [])     # fresh now
        self.assertEqual(up.calls, 1)

    def test_status_shape_and_no_secret_fields(self):
        c = self.provider(FakeUpstream([make_place()]))
        before = cache_status(c, {"demo": AREA})["areas"][0]
        self.assertEqual((before["status"], before["places"], before["data_fetched_at"]), ("miss", 0, None))
        c.refresh(AREA)
        after = cache_status(c, {"demo": AREA})
        self.assertEqual(after["areas"][0]["status"], "fresh")
        self.assertEqual(after["areas"][0]["places"], 1)
        self.assertEqual(after["api_version"], "1")


class EndpointTests(unittest.TestCase):
    def test_status_endpoint_runs_without_network(self):
        with TestClient(app) as client:
            r = client.get("/v1/cache/status")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["provider"], "brightdata")
        self.assertIn(body["areas"][0]["status"], ("fresh", "stale", "miss"))
        self.assertFalse(body["areas"][0]["refreshing"])     # prefetch disabled in tests


if __name__ == "__main__":
    unittest.main()
