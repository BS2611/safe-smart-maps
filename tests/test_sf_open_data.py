"""SF open data (311 streetlight outages, incidents) and the transit placeholder.
Socrata answers are hand-written FIXTURES via httpx.MockTransport. No network."""
from datetime import datetime, timezone

import httpx
import pytest

from server.data.models import BoundingBox
from server.data.sf_open_data import SfDataError, SocrataClient, parse_incidents, parse_outages
from server.data.transit import NoTransitProvider

NOW = datetime(2026, 10, 24, 22, 0, tzinfo=timezone.utc)
AREA = BoundingBox(37.80, -122.45, 37.81, -122.44)


def mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parse_outages_and_incidents_skip_bad_rows():
    outages = parse_outages([
        {"lat": "37.79", "long": "-122.47", "requested_datetime": "2026-10-23"},
        {"lat": "x", "long": "y"}, {}])
    assert len(outages) == 1 and outages[0].lat == 37.79 and outages[0].lng == -122.47
    incidents = parse_incidents([
        {"latitude": "37.8", "longitude": "-122.4", "incident_category": "Theft"}, {"latitude": None}])
    assert len(incidents) == 1 and incidents[0].category == "Theft"


def test_socrata_queries_and_parses():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if "vw6y-z8j6" in request.url.path:
            return httpx.Response(200, json=[{"lat": "37.8", "long": "-122.44"}])
        return httpx.Response(200, json=[{"latitude": "37.8", "longitude": "-122.44",
                                          "incident_category": "Other"}])

    sf = SocrataClient(client=mock_client(handler))
    assert len(sf.get_open_outages(AREA)) == 1
    assert len(sf.get_recent_incidents(AREA, now=NOW)) == 1
    where = seen[0].url.params["$where"]
    assert "Streetlights" in where and "Open" in where and "within_box" in where
    assert "2026-07-26" in seen[1].url.params["$where"]  # 90 days before NOW
    assert "safe-smart-maps" in seen[0].headers["user-agent"]


@pytest.mark.parametrize(
    ("response", "kind"),
    [(httpx.Response(500), "failed"), (httpx.Response(200, text="nope"), "failed"),
     (httpx.Response(200, json={"error": "x"}), "failed"), (httpx.TimeoutException("t"), "timeout"),
     (httpx.ConnectError("c"), "failed")],
)
def test_socrata_errors(response, kind):
    def handler(request):
        if isinstance(response, Exception):
            raise response
        return response

    with pytest.raises(SfDataError) as exc:
        SocrataClient(client=mock_client(handler)).get_open_outages(AREA)
    assert exc.value.kind == kind and exc.value.source == "sf311"
    assert "37.8" not in str(exc.value) and "-122" not in str(exc.value)


def test_incidents_errors_name_their_own_source():
    with pytest.raises(SfDataError) as exc:
        SocrataClient(client=mock_client(lambda r: httpx.Response(503))).get_recent_incidents(AREA, now=NOW)
    assert exc.value.source == "sf_incidents" and "HTTP 503" in str(exc.value)


def test_no_transit_provider_always_says_unknown():
    assert NoTransitProvider().get_active_stops(AREA, NOW) is None
