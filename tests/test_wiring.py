"""The real app wiring (server/main.py + server/wiring.py) starts and degrades honestly. No network:
Mapbox has no token here, so the first call stops before any request is made."""
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.services.planner import RoutePlanner
from tests import fakes

BODY = {
    "from": {"lat": fakes.ORIGIN[1], "lng": fakes.ORIGIN[0]},
    "to": {"lat": fakes.DEST[1], "lng": fakes.DEST[0]},
    "depart_time": "2026-10-24T20:00:00-07:00",
}


@pytest.fixture
def clean_app(monkeypatch, tmp_path):
    for var in ("MAPBOX_TOKEN", "BRIGHTDATA_API_KEY", "ANTHROPIC_API_KEY", "PREWARM_DEMO"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "places"))
    monkeypatch.setenv("PREFETCH_ON_STARTUP", "0")
    # The app lifespan calls load_dotenv(); without this it would put the real keys from the
    # repo-root .env back and the test would make real Mapbox/Overpass/Anthropic calls.
    monkeypatch.setattr("server.main.load_dotenv", lambda *a, **k: False)
    if hasattr(app.state, "planner"):
        del app.state.planner
    yield app
    if hasattr(app.state, "planner"):
        del app.state.planner


def test_startup_builds_the_real_planner_sharing_the_places_cache(clean_app):
    with TestClient(clean_app):
        planner = clean_app.state.planner
        assert isinstance(planner, RoutePlanner)
        assert planner.p.places is clean_app.state.places_provider   # one cache for status + routes


def test_without_a_mapbox_token_routes_answer_503_not_configured(clean_app):
    with TestClient(clean_app) as client:
        resp = client.post("/v1/routes", json=BODY)
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "NOT_CONFIGURED"
    assert "pk." not in resp.text


def test_cache_status_and_health_are_still_served(clean_app):
    with TestClient(clean_app) as client:
        assert client.get("/v1/health").status_code == 200
        status = client.get("/v1/cache/status").json()
        assert status["provider"] == "brightdata" and status["areas"][0]["status"] == "miss"
