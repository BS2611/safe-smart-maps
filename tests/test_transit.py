"""511 transit: parsing, provider errors, the transit factor and planner wiring. Fixtures are hand-written."""
import json
from datetime import timedelta, timezone

import httpx
import pytest

from server.data.models import BoundingBox
from server.data.transit import (
    Arrival,
    Muni511Provider,
    TransitError,
    TransitSnapshot,
    parse_arrivals,
    parse_stops,
)
from server.services.segment_scoring import SegmentScorer
from tests.test_extra_factors import PARAMS
from tests.test_planner import PlannerCase, request
from tests.test_segment_scoring import CFG, EVENING, SEG, area, north, road

NOW = EVENING.astimezone(timezone.utc)
STOPS = {"s1": (north(25)[0], north(25)[1]), "far": (north(900)[0], north(900)[1])}


def stop_json():
    return {"Contents": {"dataObjects": {"ScheduledStopPoint": [
        {"id": "s1", "Location": {"Latitude": str(STOPS["s1"][0]), "Longitude": str(STOPS["s1"][1])}},
        {"id": "bad", "Location": {}}]}}}


def visit(stop, minutes, line="5"):
    when = (NOW + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"MonitoringRef": stop, "MonitoredVehicleJourney": {
        "LineRef": line, "MonitoredCall": {"ExpectedArrivalTime": when}}}


def monitoring_json(*visits):
    return {"ServiceDelivery": {"StopMonitoringDelivery": {"MonitoredStopVisit": list(visits)}}}


def snapshot(*mins, stop="s1"):
    arrivals = [Arrival(stop, "5", *STOPS[stop], NOW + timedelta(minutes=m)) for m in mins]
    return TransitSnapshot(arrivals, NOW, NOW + timedelta(minutes=30))


def scorer(snap):
    return SegmentScorer(CFG, [], area([road()]), transit=snap)


def test_parse_stops_skips_bad_rows():
    assert list(parse_stops(stop_json())) == ["s1"]


def test_parse_arrivals_drops_unknown_stops_and_late_ones():
    data = monitoring_json(visit("s1", 5), visit("nope", 5), visit("s1", 90))
    got = parse_arrivals(data, {"s1": STOPS["s1"]}, NOW, horizon_min=30)
    assert [a.stop_id for a in got] == ["s1"]


def mock_provider(handler, key="fixture-key"):
    return Muni511Provider(api_key=key, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_provider_fetches_stops_once_and_arrivals_each_time():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        body = stop_json() if request.url.path.endswith("/stops") else monitoring_json(visit("s1", 5))
        return httpx.Response(200, content=("﻿" + json.dumps(body)).encode("utf-8"))

    p = mock_provider(handler)
    assert len(p.get_snapshot(NOW).arrivals) == 1
    p.get_snapshot(NOW)
    assert paths.count("/transit/stops") == 1 and paths.count("/transit/StopMonitoring") == 2


@pytest.mark.parametrize("response,kind", [
    (httpx.Response(429), "rate_limited"), (httpx.Response(500), "failed"),
    (httpx.Response(200, text="not json"), "failed")])
def test_provider_errors_have_kinds_and_no_token(response, kind):
    with pytest.raises(TransitError) as e:
        mock_provider(lambda r: response, key="SECRET-TOKEN").get_snapshot(NOW)
    assert e.value.kind == kind and "SECRET-TOKEN" not in str(e.value)


def test_provider_without_key_is_not_configured(monkeypatch):
    monkeypatch.delenv("API_511_KEY", raising=False)
    with pytest.raises(TransitError) as e:
        Muni511Provider(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))).get_snapshot(NOW)
    assert e.value.kind == "not_configured"


def test_provider_timeout_and_network_errors():
    def slow(request):
        raise httpx.ReadTimeout("slow")

    def down(request):
        raise httpx.ConnectError("down")

    for handler, kind in ((slow, "timeout"), (down, "failed")):
        with pytest.raises(TransitError) as e:
            mock_provider(handler).get_snapshot(NOW)
        assert e.value.kind == kind


def test_snapshot_within_area_filters_by_box():
    snap = TransitSnapshot(snapshot(5).arrivals + snapshot(5, stop="far").arrivals, NOW, NOW)
    tight = BoundingBox(37.7995, -122.4505, 37.8010, -122.4495)
    assert [a.stop_id for a in snap.within(tight).arrivals] == ["s1"]


def test_factor_counts_arrivals_near_the_arrival_time():
    table = PARAMS["transit_by_count"]
    f = lambda snap: scorer(snap).score_segment(SEG, NOW).factors["transit"]   # noqa: E731
    assert f(snapshot()).value == table[0]               # live feed worked, nothing coming: a known 0
    assert f(snapshot(4)).value == table[1]
    assert f(snapshot(4, 8)).value == table[2]
    assert f(snapshot(4, 8, 12, 14)).value == table[3]
    assert f(snapshot(40)).value == table[0]             # outside the window after arrival
    assert f(snapshot(4, stop="far")).value == table[0]  # too far from the segment


def test_factor_is_not_sure_without_feed_or_outside_its_horizon():
    assert scorer(None).score_segment(SEG, NOW).factors["transit"].value is None
    later = NOW + timedelta(hours=3)
    f = scorer(snapshot(4)).score_segment(SEG, later).factors["transit"]
    assert f.value is None and "next ~30 minutes" in f.reason


class FakeTransit:
    def __init__(self, snap=None, error=None):
        self.snap, self.error, self.calls = snap, error, 0

    def get_snapshot(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.snap


class TransitPlanner(PlannerCase):
    def test_default_planner_keeps_transit_not_sure(self):
        seg = self.planner().plan(request()).routes[0].segments[0]
        assert "transit" in seg.unknown_factors

    def test_failure_warns_but_not_configured_does_not(self):
        warned = self.planner(transit=FakeTransit(error=TransitError("failed", "x"))).plan(request())
        assert any("Live transit arrivals" in w for w in warned.warnings)
        quiet = self.planner(transit=FakeTransit(error=TransitError("not_configured", "x"))).plan(request())
        assert not any("transit" in w.lower() for w in quiet.warnings)

    def test_snapshot_is_cached_between_requests(self):
        fake = FakeTransit(snap=TransitSnapshot([], NOW, NOW))
        planner = self.planner(transit=fake)
        planner.plan(request())
        planner.plan(request())
        assert fake.calls == 1
