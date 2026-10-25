"""API tests for GET /v1/health. Contract: docs/agent-context/CONTRACTS.md."""
from fastapi.testclient import TestClient

from server.main import app


def test_health_returns_ok_and_api_version():
    with TestClient(app) as client:  # context manager runs the startup check
        response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "api_version": "1"}


def test_startup_loads_scoring_config():
    with TestClient(app) as client:
        assert client.app.state.scoring_config["version"] == "scoring_v1"


def test_unknown_route_is_404():
    with TestClient(app) as client:
        assert client.get("/v1/does-not-exist").status_code == 404


def test_startup_builds_the_planner_and_prewarms_only_when_asked(monkeypatch):
    """Lifespan wiring, with the real providers and the prewarm thread replaced (no network)."""
    import server.main as main

    started = []
    monkeypatch.setattr(main, "build_planner", lambda cfg: object())
    monkeypatch.setattr(main, "start_prewarm_thread", lambda planner: started.append(planner))
    if hasattr(main.app.state, "planner"):
        del main.app.state.planner

    monkeypatch.delenv("PREWARM_DEMO", raising=False)
    with TestClient(main.app):
        assert started == []
    del main.app.state.planner

    monkeypatch.setenv("PREWARM_DEMO", "1")
    with TestClient(main.app):
        assert len(started) == 1
    del main.app.state.planner
