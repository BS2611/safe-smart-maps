"""HTTP tests for POST /v1/routes with a fake planner (no network). Contract: CONTRACTS.md."""
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.data.mapbox import MapboxError
from server.main import app
from server.services.schemas import RoutesResponse
from tests import fakes

BODY = {
    "from": {"lat": fakes.ORIGIN[1], "lng": fakes.ORIGIN[0]},
    "to": {"lat": fakes.DEST[1], "lng": fakes.DEST[0]},
    "depart_time": "2026-10-24T20:00:00-07:00",
    "settings": {"max_extra_minutes": 10, "with_companion": False, "priorities": ["lighting"]},
}


@pytest.fixture
def make_client(tmp_path):
    def build(**overrides) -> TestClient:
        app.state.planner = fakes.make_planner(Path(tmp_path), **overrides)
        return TestClient(app)

    yield build
    if hasattr(app.state, "planner"):
        del app.state.planner


def test_routes_ok_and_matches_schema(make_client):
    resp = make_client().post("/v1/routes", json=BODY)
    assert resp.status_code == 200
    data = resp.json()
    RoutesResponse.model_validate(data)
    assert data["api_version"] == "1" and data["scoring_version"] == "scoring_v1"
    assert {r["label"] for r in data["routes"]} <= {"safest", "balanced", "fastest"}
    assert "from" not in json.dumps(data)  # request locations are not echoed back


def test_response_has_every_contract_field(make_client):
    route = make_client().post("/v1/routes", json=BODY).json()["routes"][0]
    for key in ("label", "also_labels", "duration_min", "extra_min", "distance_m", "route_score", "continuity",
                "open_places_count", "nearest_help_point", "geometry", "segments", "explanation",
                "explanation_source"):
        assert key in route, key
    assert set(route["continuity"]) == {"coverage_pct", "longest_gap_m", "longest_gap_note", "worst_window_score"}
    seg = route["segments"][0]
    for key in ("segment_id", "start", "end", "length_m", "arrival_time", "score", "band", "factors",
                "reasons", "data_fetched_at", "confidence", "unknown_factors", "known_weight_fraction"):
        assert key in seg, key
    assert route["geometry"]["type"] == "LineString"


def test_unknown_values_are_null_not_zero(make_client):
    route = make_client(places=fakes.make_places_provider(Path(tempfile.mkdtemp()))).post(
        "/v1/routes", json=BODY).json()["routes"][0]
    assert route["open_places_count"] is None
    assert route["continuity"]["coverage_pct"] is None
    assert route["segments"][0]["factors"]["transit"] is None


def test_bad_request_has_contract_error_shape_and_no_input_echo(make_client):
    resp = make_client().post("/v1/routes", json=dict(BODY, depart_time="not a date"))
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "BAD_REQUEST" and "depart_time" in err["message"]
    assert "not a date" not in resp.text


def test_naive_datetime_rejected(make_client):
    resp = make_client().post("/v1/routes", json=dict(BODY, depart_time="2026-10-24T20:00:00"))
    assert resp.status_code == 400


def test_out_of_range_settings_rejected(make_client):
    client = make_client()
    assert client.post("/v1/routes", json=dict(BODY, settings={"max_extra_minutes": 99})).status_code == 400
    assert client.post("/v1/routes", json=dict(BODY, settings={"priorities": ["a", "b", "c"]})).status_code == 400
    assert client.post("/v1/routes", json=dict(BODY, to={"lat": 95, "lng": 0})).status_code == 400


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [("not_configured", 503, "NOT_CONFIGURED"), ("timeout", 504, "UPSTREAM_TIMEOUT"),
     ("failed", 502, "UPSTREAM_ERROR"), ("empty", 404, "NO_ROUTE")],
)
def test_routing_errors_map_to_status_and_code(make_client, kind, status, code):
    client = make_client(routing=fakes.FakeRouting(error=MapboxError("HTTP 500 pk.secret-token", kind=kind)))
    resp = client.post("/v1/routes", json=BODY)
    assert resp.status_code == status and resp.json()["error"]["code"] == code
    assert "pk.secret-token" not in resp.text


def test_no_candidates_is_404(make_client):
    resp = make_client(routing=fakes.FakeRouting(candidates=[])).post("/v1/routes", json=BODY)
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "NO_ROUTE"


def test_partial_failure_is_200_with_warnings(make_client):
    client = make_client(context=fakes.FakeContext(error=fakes.osm_down()))
    resp = client.post("/v1/routes", json=BODY)
    assert resp.status_code == 200
    assert any("OpenStreetMap" in w for w in resp.json()["warnings"])


def test_health_and_cache_status_still_work(make_client):
    client = make_client()
    assert client.get("/v1/health").json() == {"status": "ok", "api_version": "1"}


def test_cors_allows_only_the_configured_web_origin(make_client):
    from server.main import _origins
    web = _origins[0]          # whatever WEB_ORIGINS says on this machine; never "*"
    assert "*" not in _origins
    client = make_client()
    ok = client.options("/v1/routes", headers={
        "Origin": web, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    other = client.options("/v1/routes", headers={
        "Origin": "http://evil.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert ok.headers.get("access-control-allow-origin") == web
    assert "access-control-allow-origin" not in other.headers


def test_allowed_origins_parsing_and_default():
    from server.main import DEFAULT_ORIGIN, allowed_origins
    assert allowed_origins(None) == [DEFAULT_ORIGIN] == ["http://localhost:3000"]
    assert allowed_origins("") == [DEFAULT_ORIGIN]
    assert allowed_origins(" https://a.example , https://b.example ,, ") == ["https://a.example", "https://b.example"]
