"""Prewarm fills the caches for the demo corridor (labeled fakes, no network)."""
from datetime import datetime, timezone

from server.data.errors import DataSourceError
from server.services.prewarm import demo_requests, prewarm, start_prewarm_thread
from tests import fakes

SAT_3PM = datetime(2026, 10, 24, 22, 30, tzinfo=timezone.utc)


def test_demo_requests_are_8pm_and_1am_pacific():
    first, second = demo_requests(SAT_3PM)
    assert first.depart_time.isoformat() == "2026-10-24T20:00:00-07:00"
    assert second.depart_time.isoformat() == "2026-10-25T01:00:00-07:00"


def test_after_midnight_it_is_still_tonight():
    two_am = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)  # 2 AM Pacific
    first, _ = demo_requests(two_am)
    assert first.depart_time.isoformat() == "2026-10-24T20:00:00-07:00"


def test_prewarm_runs_both_trips_and_warms_the_caches():
    places, osm = fakes.FakePlaces(), fakes.FakeOsm()
    planner = fakes.make_planner(places=places, osm=osm)
    assert prewarm(planner, SAT_3PM) == {"ok": 2, "failed": 0, "errors": []}
    calls = (places.calls, osm.calls)
    from tests.test_planner import request
    planner.plan(request())                       # a real request afterwards
    assert (places.calls, osm.calls) == calls     # served from the cache


def test_prewarm_never_raises():
    planner = fakes.make_planner(routing=fakes.FakeRouting(error=fakes.not_configured()))
    result = prewarm(planner, SAT_3PM)
    assert result["failed"] == 2 and result["errors"] == ["NOT_CONFIGURED", "NOT_CONFIGURED"]
    boom = fakes.make_planner(routing=fakes.FakeRouting(error=RuntimeError("x")))
    assert prewarm(boom, SAT_3PM)["errors"] == ["RuntimeError", "RuntimeError"]
    down = fakes.make_planner(routing=fakes.FakeRouting(error=DataSourceError("m", "HTTP 500")))
    assert prewarm(down, SAT_3PM)["failed"] == 2


def test_thread_runs_in_background():
    thread = start_prewarm_thread(fakes.make_planner())
    thread.join(timeout=10)
    assert not thread.is_alive() and thread.daemon
