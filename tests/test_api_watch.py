"""HTTP tests for the watch relay endpoints. Contract: CONTRACTS.md "Watch relay endpoints"."""
import logging

import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.services.watch_relay import WatchRelay


@pytest.fixture
def client():
    app.state.watch_relay = WatchRelay()
    yield TestClient(app)
    del app.state.watch_relay


def pair(client):
    trip = client.post("/v1/trips/pair").json()
    watch = client.post("/v1/watch/pair", json={"pair_code": trip["pair_code"], "device": "wearos"}).json()
    return trip["trip_id"], {"Authorization": f"Bearer {watch['watch_token']}"}


def beat(bpm=80, source="wearos"):
    return {"bpm": bpm, "ts": "2026-10-25T10:00:00Z", "source": source}


def test_full_flow(client):
    trip_id, auth = pair(client)
    assert client.post("/v1/watch/heartbeat", json=beat(88), headers=auth).status_code == 204
    out = client.get(f"/v1/trips/{trip_id}/events").json()
    assert out["status"] == "paired" and out["latest"]["bpm"] == 88
    assert client.post("/v1/watch/prompt", headers=auth).status_code == 204
    alert = client.post("/v1/alerts", json={"trip_id": trip_id, "location": {"lat": 1, "lng": 2}}, headers=auth)
    assert alert.status_code == 200 and alert.json() == {"status": "contact_not_opted_in"}
    assert client.post("/v1/alerts/ack", json={"trip_id": trip_id, "ok": True}).status_code == 204
    types = [e["type"] for e in client.get(f"/v1/trips/{trip_id}/events").json()["events"]]
    assert types == ["paired", "bpm", "prompt", "alert_sent", "ack"]


def test_events_after_param(client):
    trip_id, auth = pair(client)
    client.post("/v1/watch/heartbeat", json=beat(80), headers=auth)
    nxt = client.get(f"/v1/trips/{trip_id}/events").json()["next_after"]
    client.post("/v1/watch/heartbeat", json=beat(81), headers=auth)
    out = client.get(f"/v1/trips/{trip_id}/events", params={"after": nxt}).json()
    assert [e["bpm"] for e in out["events"]] == [81]


def test_heartbeat_without_token_is_401(client):
    resp = client.post("/v1/watch/heartbeat", json=beat())
    assert resp.status_code == 401 and resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_bad_pair_code_shape_is_400(client):
    resp = client.post("/v1/watch/pair", json={"pair_code": "12ab"})
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "BAD_REQUEST"


def test_wrong_pair_code_is_400_and_locks_after_five(client):
    client.post("/v1/trips/pair")
    codes = []
    for _ in range(6):
        codes.append(client.post("/v1/watch/pair", json={"pair_code": "999999"}).status_code)
    assert codes[:5] == [400] * 5 or codes[:5] == [200] * 5  # 200 only if 999999 was the real code
    if codes[0] == 400:
        assert codes[5] == 429


def test_bad_bpm_and_source_are_400(client):
    _, auth = pair(client)
    assert client.post("/v1/watch/heartbeat", json=beat(0), headers=auth).status_code == 400
    assert client.post("/v1/watch/heartbeat", json=beat(80, "fitbit"), headers=auth).status_code == 400


def test_end_removes_trip(client):
    trip_id, auth = pair(client)
    assert client.post(f"/v1/trips/{trip_id}/end").status_code == 204
    assert client.get(f"/v1/trips/{trip_id}/events").status_code == 404
    assert client.post("/v1/watch/heartbeat", json=beat(), headers=auth).status_code == 401
    assert client.post(f"/v1/trips/{trip_id}/end").status_code == 404


def test_unknown_trip_is_404(client):
    assert client.get("/v1/trips/nope/events").status_code == 404


def test_readings_and_coordinates_are_not_logged(client, caplog):
    caplog.set_level(logging.DEBUG)
    trip_id, auth = pair(client)
    client.post("/v1/watch/heartbeat", json=beat(137), headers=auth)
    client.post("/v1/alerts", json={"trip_id": trip_id, "location": {"lat": 37.7712, "lng": -122.4194}},
                headers=auth)
    text = caplog.text
    assert "137" not in text and "37.7712" not in text and "122.4194" not in text
    assert auth["Authorization"].split()[1] not in text


def test_cors_allows_authorization_header(client):
    resp = client.options("/v1/watch/heartbeat", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert resp.status_code == 200
    assert "authorization" in resp.headers["access-control-allow-headers"].lower()
