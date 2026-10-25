"""The fake watch script drives the real relay endpoints (in process, no network)."""
import pytest
from fastapi.testclient import TestClient

from scripts import fake_watch
from server.main import app
from server.services.watch_relay import WatchRelay


@pytest.fixture
def client(monkeypatch):
    app.state.watch_relay = WatchRelay()
    test_client = TestClient(app)

    class InProcess:  # same calls the script uses, but straight into the app
        def __init__(self, **kwargs):
            pass

        def post(self, url, **kw):
            return test_client.post(url, **kw)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(fake_watch.httpx, "Client", InProcess)
    monkeypatch.setattr(fake_watch.time, "sleep", lambda s: None)
    yield test_client
    del app.state.watch_relay


def test_fake_watch_sends_labeled_readings_and_alert(client):
    trip = client.post("/v1/trips/pair").json()
    code = fake_watch.main(["--code", trip["pair_code"], "--seconds", "4", "--spike", "--prompt"])
    assert code == 0
    out = client.get(f"/v1/trips/{trip['trip_id']}/events").json()
    assert out["latest"]["source"] == "simulated"
    assert [e["type"] for e in out["events"]][-2:] == ["prompt", "alert_sent"]
    assert max(e["bpm"] for e in out["events"] if e["type"] == "bpm") >= 110


def test_fake_watch_ok_answer(client):
    trip = client.post("/v1/trips/pair").json()
    assert fake_watch.main(["--code", trip["pair_code"], "--seconds", "2", "--prompt", "--ok"]) == 0
    events = client.get(f"/v1/trips/{trip['trip_id']}/events").json()["events"]
    assert events[-1] == {"id": events[-1]["id"], "type": "ack", "ok": True}


def test_fake_watch_wrong_code_fails_cleanly(client, capsys):
    assert fake_watch.main(["--code", "000000", "--seconds", "1"]) == 1
    assert "Pairing failed" in capsys.readouterr().out
