"""In-memory relay between a phone web page and a watch app (CONTRACTS.md "Watch relay endpoints").

Heart-rate data is health data: it is held in memory only, with a short life, deleted when the trip
ends, and never logged. Nothing here writes to disk. One server instance only (state is not shared).
"""
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

CODE_TTL_S = 600
TRIP_IDLE_TTL_S = 1800
MAX_EVENTS = 30
MAX_FAILED_CODES = 5
LOCKOUT_WINDOW_S = 60
SOURCES = ("wearos", "band", "simulated")
BPM_MIN, BPM_MAX = 25, 250


class RelayError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class _Trip:
    trip_id: str
    code: str
    created: float
    touched: float
    token: str | None = None
    alert_status: str | None = None
    next_id: int = 1
    events: deque = field(default_factory=lambda: deque(maxlen=MAX_EVENTS))
    latest: dict | None = None

    def add(self, type_: str, **data) -> dict:
        event = {"id": self.next_id, "type": type_, **data}
        self.next_id += 1
        self.events.append(event)
        return event


class WatchRelay:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._trips: dict[str, _Trip] = {}
        self._codes: dict[str, str] = {}
        self._tokens: dict[str, str] = {}
        self._failed: list[float] = []

    # -- internals (call with the lock held) --
    def _drop(self, trip: _Trip) -> None:
        self._trips.pop(trip.trip_id, None)
        self._codes.pop(trip.code, None)
        if trip.token:
            self._tokens.pop(trip.token, None)

    def _purge(self) -> None:
        now = self._clock()
        for trip in list(self._trips.values()):
            if now - trip.touched > TRIP_IDLE_TTL_S:
                self._drop(trip)
            elif trip.token is None and now - trip.created > CODE_TTL_S:
                self._codes.pop(trip.code, None)  # code expired; the trip waits for the idle limit

    def _trip(self, trip_id: str) -> _Trip:
        trip = self._trips.get(trip_id)
        if trip is None:
            raise RelayError("NOT_FOUND", "Trip not found or already ended.")
        return trip

    def _trip_for_token(self, token: str | None) -> _Trip:
        trip_id = self._tokens.get(token or "")
        if trip_id is None:
            raise RelayError("UNAUTHORIZED", "Pair the watch first.")
        return self._trip(trip_id)

    # -- phone side --
    def create_trip(self) -> dict:
        with self._lock:
            self._purge()
            code = next(c for c in (f"{secrets.randbelow(1_000_000):06d}" for _ in range(50))
                        if c not in self._codes)
            now = self._clock()
            trip = _Trip(trip_id=secrets.token_hex(16), code=code, created=now, touched=now)
            self._trips[trip.trip_id] = trip
            self._codes[code] = trip.trip_id
            return {"trip_id": trip.trip_id, "pair_code": code, "expires_in_s": CODE_TTL_S}

    def events(self, trip_id: str, after: int = 0) -> dict:
        with self._lock:
            self._purge()
            trip = self._trip(trip_id)
            trip.touched = self._clock()
            events = [e for e in trip.events if e["id"] > after]
            return {
                "status": "paired" if trip.token else "waiting",
                "latest": trip.latest,
                "events": events,
                "next_after": trip.next_id - 1,
            }

    def end(self, trip_id: str) -> None:
        with self._lock:
            self._drop(self._trip(trip_id))

    def ack(self, trip_id: str, ok: bool) -> None:
        with self._lock:
            trip = self._trip(trip_id)
            trip.touched = self._clock()
            trip.add("ack", ok=ok)

    # -- watch side --
    def pair(self, code: str) -> dict:
        with self._lock:
            self._purge()
            now = self._clock()
            self._failed = [t for t in self._failed if now - t < LOCKOUT_WINDOW_S]
            if len(self._failed) >= MAX_FAILED_CODES:
                raise RelayError("TOO_MANY_ATTEMPTS", "Too many wrong codes. Wait a minute and try again.")
            trip_id = self._codes.get(code)
            trip = self._trips.get(trip_id) if trip_id else None
            if trip is None or trip.token is not None:
                self._failed.append(now)
                raise RelayError("BAD_CODE", "That code is not valid. Check the code on your phone.")
            trip.token = secrets.token_urlsafe(24)
            trip.touched = now
            self._tokens[trip.token] = trip.trip_id
            self._codes.pop(trip.code, None)  # a code works once
            trip.add("paired")
            return {"watch_token": trip.token, "trip_id": trip.trip_id}

    def heartbeat(self, token: str | None, bpm: int, ts: str, source: str) -> None:
        if source not in SOURCES:
            raise RelayError("BAD_REQUEST", "Unknown source.")
        if not BPM_MIN <= bpm <= BPM_MAX:
            raise RelayError("BAD_REQUEST", "Reading out of range.")
        with self._lock:
            trip = self._trip_for_token(token)
            trip.touched = self._clock()
            trip.latest = {"bpm": bpm, "ts": ts, "source": source}
            trip.add("bpm", **trip.latest)

    def prompt(self, token: str | None) -> None:
        with self._lock:
            trip = self._trip_for_token(token)
            trip.touched = self._clock()
            trip.add("prompt")

    def alert(self, token: str | None, trip_id: str) -> str:
        """Records the alert. No message provider exists yet (OPEN_QUESTIONS 13), so nothing is sent."""
        with self._lock:
            trip = self._trip_for_token(token)
            if trip.trip_id != trip_id:
                raise RelayError("UNAUTHORIZED", "This watch is not paired to that trip.")
            trip.touched = self._clock()
            trip.alert_status = "contact_not_opted_in"
            trip.add("alert_sent", status=trip.alert_status)
            return trip.alert_status
