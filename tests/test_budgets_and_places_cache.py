"""Time budgets (a slow source must not hold a request for minutes), in-flight sharing, and the disk copy
of live listings. Labeled fakes only, no network."""
import threading
import time
from datetime import datetime, timezone

import pytest

from server.data.errors import DataSourceError
from server.data.models import BoundingBox
from server.data.places_cache import CachedPlacesProvider, place_from_json, place_to_json
from server.data.transit import NoTransitProvider
from server.services.planner import Providers, RoutePlanner, places_cells
from server.services.scoring_config import load_scoring_config
from tests import fakes
from tests.test_planner import request

AREA = BoundingBox(37.80, -122.45, 37.806, -122.444)
WHEN = datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc)


class SlowPlaces(fakes.FakePlaces):
    """Answers only after `release` is set, like a live lookup that takes a minute."""

    def __init__(self):
        super().__init__()
        self.release = threading.Event()
        self.started = threading.Event()

    def get_places(self, area, time):
        self.started.set()
        self.release.wait(timeout=20)
        return super().get_places(area, time)


def planner_with(places, budget=0.3, osm=None):
    providers = Providers(routing=fakes.FakeRouting(), places=places, osm=osm or fakes.FakeOsm(),
                          sf=fakes.FakeSf(), transit=NoTransitProvider(), explainer=fakes.FakeExplainer())
    return RoutePlanner(providers, load_scoring_config(), budgets={"places": budget, "default": budget})


def test_slow_listings_do_not_hold_the_request_and_are_reported_as_still_loading():
    places = SlowPlaces()
    planner = planner_with(places)
    began = time.monotonic()
    resp = planner.plan(request())
    assert time.monotonic() - began < 5
    assert any("Live business listings" in w and "still loading" in w for w in resp.warnings)
    assert resp.routes and all(r.open_places_count is None for r in resp.routes)
    assert all(s.factors["open_places"] is None for s in resp.routes[0].segments)
    places.release.set()


def test_the_slow_lookup_keeps_running_and_the_next_request_is_complete():
    places = SlowPlaces()
    planner = planner_with(places)
    first = planner.plan(request())
    assert any("still loading" in w for w in first.warnings)
    places.release.set()
    deadline = time.monotonic() + 10
    second = first
    while time.monotonic() < deadline:        # the background lookups finish and fill the cache
        second = planner.plan(request())
        if not any("Live business listings" in w for w in second.warnings):
            break
        time.sleep(0.1)
    assert not any("Live business listings" in w for w in second.warnings)
    assert second.routes[0].open_places_count is not None


def test_two_requests_at_once_share_one_lookup_per_area():
    places = SlowPlaces()
    planner = planner_with(places, budget=1.0)
    out = []
    threads = [threading.Thread(target=lambda: out.append(planner.plan(request()))) for _ in range(2)]
    for t in threads:
        t.start()
    places.started.wait(timeout=5)
    time.sleep(0.3)
    places.release.set()
    for t in threads:
        t.join(timeout=15)
    assert len(out) == 2
    n_cells = len(places_cells([c.coords for c in fakes.FakeRouting().candidates]))
    assert places.calls == n_cells            # each area was asked for once, not twice


def test_a_slow_map_service_is_reported_not_waited_for():
    gate = threading.Event()

    class SlowOsm(fakes.FakeOsm):
        def get_map_features(self, area):
            gate.wait(timeout=20)
            return super().get_map_features(area)

    planner = planner_with(fakes.FakePlaces(), osm=SlowOsm())
    began = time.monotonic()
    resp = planner.plan(request())
    assert time.monotonic() - began < 5
    assert any("Street and lighting map data" in w and "still loading" in w for w in resp.warnings)
    assert all(s.factors["main_road"] is None for s in resp.routes[0].segments)
    gate.set()


# ---------- disk copy of live listings ----------

def test_places_roundtrip_through_json():
    for p in fakes.places():
        assert place_from_json(place_to_json(p)) == p
    assert place_from_json(place_to_json(fakes.place("X", -122.4, 37.8, "cafe", None))).weekly_hours is None


def test_fresh_copy_is_used_without_calling_the_provider(tmp_path):
    inner = fakes.FakePlaces()
    clock = [1000.0]
    provider = CachedPlacesProvider(inner, tmp_path, ttl_s=3600, clock=lambda: clock[0])
    first = provider.get_places(AREA, WHEN)
    calls = inner.calls
    clock[0] += 600
    again = provider.get_places(AREA, WHEN)
    assert inner.calls == calls and again == first and first


def test_expired_copy_is_refreshed(tmp_path):
    inner = fakes.FakePlaces()
    clock = [1000.0]
    provider = CachedPlacesProvider(inner, tmp_path, ttl_s=3600, clock=lambda: clock[0])
    provider.get_places(AREA, WHEN)
    calls = inner.calls
    clock[0] += 7200
    provider.get_places(AREA, WHEN)
    assert inner.calls == calls + 1


def test_old_copy_is_used_when_the_live_lookup_fails(tmp_path):
    inner = fakes.FakePlaces()
    clock = [1000.0]
    provider = CachedPlacesProvider(inner, tmp_path, ttl_s=3600, clock=lambda: clock[0])
    saved = provider.get_places(AREA, WHEN)
    inner.error = DataSourceError("brightdata", "HTTP 500")
    clock[0] += 7200
    assert provider.get_places(AREA, WHEN) == saved           # an old copy beats nothing


def test_failure_without_any_copy_still_raises(tmp_path):
    provider = CachedPlacesProvider(fakes.FakePlaces(error=DataSourceError("brightdata", "HTTP 500")), tmp_path)
    with pytest.raises(DataSourceError):
        provider.get_places(AREA, WHEN)


def test_corrupt_copy_is_ignored_and_no_folder_means_no_saving(tmp_path):
    inner = fakes.FakePlaces()
    provider = CachedPlacesProvider(inner, tmp_path)
    name = f"{AREA.south:.4f}_{AREA.west:.4f}_{AREA.north:.4f}_{AREA.east:.4f}.json"
    (tmp_path / name).write_text("{x", encoding="utf-8")
    assert provider.get_places(AREA, WHEN)
    memory_only = CachedPlacesProvider(inner, None)
    memory_only.get_places(AREA, WHEN)
    calls = inner.calls
    memory_only.get_places(AREA, WHEN)
    assert inner.calls == calls + 1                           # nothing saved, so every call goes through


def test_unwritable_folder_does_not_break_the_lookup(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    provider = CachedPlacesProvider(fakes.FakePlaces(), blocker / "sub")
    assert provider.get_places(AREA, WHEN)
