"""Unit tests for the in-memory watch relay (no network, fake clock)."""
import pytest

from server.services.watch_relay import (
    CODE_TTL_S,
    MAX_EVENTS,
    MAX_FAILED_CODES,
    TRIP_IDLE_TTL_S,
    RelayError,
    WatchRelay,
)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def relay(clock):
    return WatchRelay(clock=clock)


def paired(relay):
    trip = relay.create_trip()
    watch = relay.pair(trip["pair_code"])
    return trip["trip_id"], watch["watch_token"]


def code_of(exc_info) -> str:
    return exc_info.value.code


def test_create_trip_gives_six_digit_code_and_waiting_status(relay):
    trip = relay.create_trip()
    assert len(trip["pair_code"]) == 6 and trip["pair_code"].isdigit()
    assert trip["expires_in_s"] == CODE_TTL_S
    assert len(trip["trip_id"]) == 32
    assert relay.events(trip["trip_id"])["status"] == "waiting"


def test_pair_links_watch_and_code_works_once(relay):
    trip = relay.create_trip()
    watch = relay.pair(trip["pair_code"])
    assert watch["trip_id"] == trip["trip_id"] and watch["watch_token"]
    assert relay.events(trip["trip_id"])["status"] == "paired"
    with pytest.raises(RelayError) as e:
        relay.pair(trip["pair_code"])
    assert code_of(e) == "BAD_CODE"


def test_code_expires_after_ten_minutes(relay, clock):
    trip = relay.create_trip()
    clock.now += CODE_TTL_S + 1
    with pytest.raises(RelayError) as e:
        relay.pair(trip["pair_code"])
    assert code_of(e) == "BAD_CODE"


def test_wrong_codes_lock_out_then_recover(relay, clock):
    trip = relay.create_trip()
    wrong = "000000" if trip["pair_code"] != "000000" else "111111"
    for _ in range(MAX_FAILED_CODES):
        with pytest.raises(RelayError) as e:
            relay.pair(wrong)
        assert code_of(e) == "BAD_CODE"
    with pytest.raises(RelayError) as e:
        relay.pair(trip["pair_code"])  # even the right code is refused while locked
    assert code_of(e) == "TOO_MANY_ATTEMPTS"
    clock.now += 61
    assert relay.pair(trip["pair_code"])["trip_id"] == trip["trip_id"]


def test_heartbeat_needs_a_valid_token(relay):
    with pytest.raises(RelayError) as e:
        relay.heartbeat(None, 80, "2026-10-25T10:00:00Z", "wearos")
    assert code_of(e) == "UNAUTHORIZED"
    with pytest.raises(RelayError) as e:
        relay.heartbeat("not-a-token", 80, "2026-10-25T10:00:00Z", "wearos")
    assert code_of(e) == "UNAUTHORIZED"


def test_heartbeat_stores_latest_and_event(relay):
    trip_id, token = paired(relay)
    relay.heartbeat(token, 82, "2026-10-25T10:00:00Z", "wearos")
    out = relay.events(trip_id)
    assert out["latest"] == {"bpm": 82, "ts": "2026-10-25T10:00:00Z", "source": "wearos"}
    assert [e["type"] for e in out["events"]] == ["paired", "bpm"]


@pytest.mark.parametrize("bpm", [0, 24, 251, 400])
def test_out_of_range_bpm_rejected(relay, bpm):
    _, token = paired(relay)
    with pytest.raises(RelayError) as e:
        relay.heartbeat(token, bpm, "2026-10-25T10:00:00Z", "wearos")
    assert code_of(e) == "BAD_REQUEST"


def test_unknown_source_rejected(relay):
    _, token = paired(relay)
    with pytest.raises(RelayError):
        relay.heartbeat(token, 80, "2026-10-25T10:00:00Z", "fitbit")


def test_simulated_source_is_kept_as_simulated(relay):
    trip_id, token = paired(relay)
    relay.heartbeat(token, 90, "2026-10-25T10:00:00Z", "simulated")
    assert relay.events(trip_id)["latest"]["source"] == "simulated"


def test_events_after_returns_only_newer(relay):
    trip_id, token = paired(relay)
    relay.heartbeat(token, 80, "t1", "wearos")
    first = relay.events(trip_id)
    relay.heartbeat(token, 81, "t2", "wearos")
    newer = relay.events(trip_id, after=first["next_after"])
    assert [e["bpm"] for e in newer["events"]] == [81]
    assert relay.events(trip_id, after=newer["next_after"])["events"] == []


def test_event_buffer_is_capped(relay):
    trip_id, token = paired(relay)
    for i in range(MAX_EVENTS + 10):
        relay.heartbeat(token, 70 + i % 20, f"t{i}", "wearos")
    assert len(relay.events(trip_id)["events"]) == MAX_EVENTS


def test_token_of_one_trip_cannot_alert_another(relay):
    _, token_a = paired(relay)
    trip_b, _ = paired(relay)
    with pytest.raises(RelayError) as e:
        relay.alert(token_a, trip_b)
    assert code_of(e) == "UNAUTHORIZED"


def test_prompt_alert_and_ack_flow(relay):
    trip_id, token = paired(relay)
    relay.prompt(token)
    assert relay.alert(token, trip_id) == "contact_not_opted_in"  # nothing is really sent yet
    relay.ack(trip_id, True)
    types = [e["type"] for e in relay.events(trip_id)["events"]]
    assert types == ["paired", "prompt", "alert_sent", "ack"]


def test_end_deletes_everything(relay):
    trip_id, token = paired(relay)
    relay.heartbeat(token, 80, "t", "wearos")
    relay.end(trip_id)
    with pytest.raises(RelayError) as e:
        relay.events(trip_id)
    assert code_of(e) == "NOT_FOUND"
    with pytest.raises(RelayError) as e:
        relay.heartbeat(token, 80, "t", "wearos")  # token died with the trip
    assert code_of(e) == "UNAUTHORIZED"


def test_idle_trip_is_removed(relay, clock):
    trip_id, _ = paired(relay)
    clock.now += TRIP_IDLE_TTL_S + 1
    with pytest.raises(RelayError) as e:
        relay.events(trip_id)
    assert code_of(e) == "NOT_FOUND"
