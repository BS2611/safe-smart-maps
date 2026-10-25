"""Apify places fallback. Apify answers are hand-written FIXTURES shaped like a real run (checked live)."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from server.data.apify import (
    ApifyError,
    ApifyPlacesProvider,
    FallbackPlacesProvider,
    normalize_record,
)
from server.data.models import BoundingBox
from server.data.opening_hours import OpenStatus, evaluate_open_status

AREA = BoundingBox(south=37.797, west=-122.455, north=37.809, east=-122.440)
NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)
HOURS = [{"day": d, "hours": "8 AM to 2:30 PM"} for d in
         ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")] + [
    {"day": "Saturday", "hours": "Closed"}, {"day": "Sunday", "hours": "Closed"}]


def rec(**kw):
    base = {"title": "Cafe RX", "categoryName": "Cafe", "location": {"lat": 37.8003, "lng": -122.4519},
            "openingHours": HOURS, "placeId": "ChIJx", "permanentlyClosed": False, "temporarilyClosed": False}
    return {**base, **kw}


def provider(handler, **kw):
    return ApifyPlacesProvider(client=httpx.Client(transport=httpx.MockTransport(handler)), **kw)


def test_normalize_reads_hours_with_narrow_spaces():
    p = normalize_record(rec(), NOW)
    assert (p.name, p.category, p.source, p.place_id) == ("Cafe RX", "cafe", "apify", "ChIJx")
    pt = ZoneInfo("America/Los_Angeles")
    assert evaluate_open_status(p, datetime(2026, 10, 26, 10, 0, tzinfo=pt)) is OpenStatus.OPEN
    assert evaluate_open_status(p, datetime(2026, 10, 26, 20, 0, tzinfo=pt)) is OpenStatus.CLOSED
    assert evaluate_open_status(p, datetime(2026, 10, 24, 10, 0, tzinfo=pt)) is OpenStatus.CLOSED   # Saturday


@pytest.mark.parametrize("bad", [
    rec(permanentlyClosed=True), rec(temporarilyClosed=True), rec(title=""), rec(location={}), "oops"])
def test_normalize_drops_unusable_records(bad):
    assert normalize_record(bad, NOW) is None


def test_missing_hours_stay_unknown_not_closed():
    p = normalize_record(rec(openingHours=None), NOW)
    assert evaluate_open_status(p, datetime(2026, 10, 26, 10, 0, tzinfo=ZoneInfo("America/Los_Angeles"))) is OpenStatus.UNKNOWN


def test_get_places_sends_capped_polygon_request_and_filters_results(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "fixture-token")
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        outside = rec(title="Far", placeId="far", location={"lat": 38.5, "lng": -122.4})
        return httpx.Response(201, json=[rec(), rec(), outside])     # duplicate and outside the area

    places = provider(handler, limit_per_keyword=7).get_places(AREA, NOW)
    assert [p.name for p in places] == ["Cafe RX"]
    assert seen["auth"] == "Bearer fixture-token"
    assert seen["body"]["maxCrawledPlacesPerSearch"] == 7 and seen["body"]["customGeolocation"]["type"] == "Polygon"


@pytest.mark.parametrize("response", [httpx.Response(402), httpx.Response(500), httpx.Response(200, text="oops"),
                                      httpx.Response(200, json={"a": 1})])
def test_errors_hide_the_token(monkeypatch, response):
    monkeypatch.setenv("APIFY_TOKEN", "SECRET-TOKEN")
    with pytest.raises(ApifyError) as e:
        provider(lambda r: response).get_places(AREA, NOW)
    assert "SECRET-TOKEN" not in str(e.value)


def test_no_token_raises(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    assert not ApifyPlacesProvider.configured()
    with pytest.raises(ApifyError):
        provider(lambda r: httpx.Response(200, json=[])).get_places(AREA, NOW)


class Stub:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    def get_places(self, area, time):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def test_fallback_uses_secondary_only_when_primary_fails():
    ok, backup = Stub(["bd"]), Stub(["apify"])
    f = FallbackPlacesProvider(ok, backup)
    assert f.get_places(AREA, NOW) == ["bd"] and backup.calls == 0 and f.last_source == "primary"
    f = FallbackPlacesProvider(Stub(error=RuntimeError("down")), backup)
    assert f.get_places(AREA, NOW) == ["apify"] and f.last_source == "secondary"


def test_fallback_reraises_when_secondary_not_configured_or_also_fails():
    with pytest.raises(RuntimeError, match="down"):
        FallbackPlacesProvider(Stub(error=RuntimeError("down")), Stub(["x"]), lambda: False).get_places(AREA, NOW)
    with pytest.raises(ValueError):
        FallbackPlacesProvider(Stub(error=RuntimeError("down")), Stub(error=ValueError("also"))).get_places(AREA, NOW)
