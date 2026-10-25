"""HTTP tests for POST /v1/routes with a fake planner (no network). Contract: CONTRACTS.md."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.data.errors import DataSourceError
from server.main import app
from server.services.schemas import RoutesResponse
from tests import fakes

FIXTURES = Path(__file__).parent / "fixtures"

BODY = {
    "from": {"lat": fakes.ORIGIN[1], "lng": fakes.ORIGIN[0]},
    "to": {"lat": fakes.DEST[1], "lng": fakes.DEST[0]},
    "depart_time": "2026-10-24T20:00:00-07:00",
    "settings": {"max_extra_minutes": 10, "with_companion": False, "priorities": ["lighting"]},
}


def client_with(planner):
    app.state.planner = planner
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_planner():
    yield
    if hasattr(app.state, "planner"):
        del app.state.planner


def test_routes_ok_and_matches_schema():
    with client_with(fakes.make_planner()) as client:
        resp = client.post("/v1/routes", json=BODY)
    assert resp.status_code == 200
    data = resp.json()
    RoutesResponse.model_validate(data)
    assert data["api_version"] == "1" and data["scoring_version"] == "scoring_v1"
    assert {r["label"] for r in data["routes"]} <= {"safest", "balanced", "fastest"}
    assert "from" not in json.dumps(data)  # request locations are not echoed back


@pytest.mark.parametrize("name", ["routes_response.json", "routes_response_1am.json"])
def test_committed_fixture_is_current_contract_output(name):
    """The web app tests against tests/fixtures/routes_response.json. If this fails, the API
    output changed: run `python -m tests.make_fixture`, check the diff, and tell the web side."""
    from tests.make_fixture import build_fixture
    assert json.loads((FIXTURES / name).read_text(encoding="utf-8")) == build_fixture(name)


def test_bad_request_has_contract_error_shape_and_no_input_echo():
    bad = dict(BODY, depart_time="not a date")
    with client_with(fakes.make_planner()) as client:
        resp = client.post("/v1/routes", json=bad)
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "BAD_REQUEST" and "depart_time" in err["message"]
    assert "not a date" not in resp.text


def test_naive_datetime_rejected():
    with client_with(fakes.make_planner()) as client:
        resp = client.post("/v1/routes", json=dict(BODY, depart_time="2026-10-24T20:00:00"))
    assert resp.status_code == 400


def test_out_of_range_settings_rejected():
    body = dict(BODY, settings={"max_extra_minutes": 99})
    with client_with(fakes.make_planner()) as client:
        assert client.post("/v1/routes", json=body).status_code == 400
        body = dict(BODY, settings={"priorities": ["a", "b", "c"]})
        assert client.post("/v1/routes", json=body).status_code == 400


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [(fakes.not_configured(), 503, "NOT_CONFIGURED"),
     (DataSourceError("mapbox", "slow", kind="timeout"), 504, "UPSTREAM_TIMEOUT"),
     (DataSourceError("mapbox", "HTTP 500"), 502, "UPSTREAM_ERROR")],
)
def test_upstream_errors_map_to_status_and_code(error, status, code):
    planner = fakes.make_planner(routing=fakes.FakeRouting(error=error))
    with client_with(planner) as client:
        resp = client.post("/v1/routes", json=BODY)
    assert resp.status_code == status and resp.json()["error"]["code"] == code
    assert "MAPBOX" not in resp.text.replace("MAPBOX_TOKEN", "")  # no secrets or URLs


def test_no_route_is_404():
    planner = fakes.make_planner(routing=fakes.FakeRouting(candidates=[]))
    with client_with(planner) as client:
        resp = client.post("/v1/routes", json=BODY)
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "NO_ROUTE"


def test_cors_allows_only_the_configured_web_origin():
    from server.main import _origins
    web = _origins[0]          # whatever WEB_ORIGINS says on this machine; never "*"
    assert "*" not in _origins
    with client_with(fakes.make_planner()) as client:
        ok = client.options("/v1/routes", headers={
            "Origin": web, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"})
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
