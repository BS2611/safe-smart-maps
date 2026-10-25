"""Prewarm runs the demo trip so the first real request is fast (labeled fakes, no network)."""
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from server.data.mapbox import MapboxError
from server.services.prewarm import demo_request, prewarm, start_prewarm_thread
from tests import fakes
from tests.test_planner import request

SAT_3PM = datetime(2026, 10, 24, 22, 30, tzinfo=timezone.utc)


def planner(**overrides):
    return fakes.make_planner(Path(tempfile.mkdtemp()), **overrides)


def test_demo_request_is_8pm_pacific_tonight():
    assert demo_request(SAT_3PM).depart_time.isoformat() == "2026-10-24T20:00:00-07:00"


def test_after_midnight_it_is_still_tonight():
    two_am = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)  # 2 AM Pacific
    assert demo_request(two_am).depart_time.isoformat() == "2026-10-24T20:00:00-07:00"


def test_demo_request_is_the_palace_to_montgomery_trip():
    req = demo_request(SAT_3PM)
    assert (req.from_.lat, req.from_.lng) == (37.8029, -122.4484)
    assert (req.to.lat, req.to.lng) == (37.7894, -122.4013)


def test_prewarm_loads_map_data_once_and_a_real_request_reuses_it():
    ctx = fakes.FakeContext()
    p = planner(context=ctx)
    assert prewarm(p, SAT_3PM) == {"ok": 1, "failed": 0, "errors": []}
    assert ctx.calls == 1
    p.plan(request())
    assert ctx.calls == 1          # same area: served from the cache


def test_prewarm_never_raises():
    not_set = planner(routing=fakes.FakeRouting(error=MapboxError("x", kind="not_configured")))
    assert prewarm(not_set, SAT_3PM) == {"ok": 0, "failed": 1, "errors": ["NOT_CONFIGURED"]}
    boom = planner(routing=fakes.FakeRouting(error=RuntimeError("x")))
    assert prewarm(boom, SAT_3PM) == {"ok": 0, "failed": 1, "errors": ["RuntimeError"]}


def test_thread_runs_in_background():
    thread = start_prewarm_thread(planner())
    thread.join(timeout=10)
    assert not thread.is_alive() and thread.daemon
