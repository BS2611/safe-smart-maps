"""Transit from 511.org (SFMTA / Muni): live predicted arrivals, one request for the whole agency.

Honest limits: this is a LIVE feed, so it only says what is arriving in the next ~30 minutes. A trip
planned for later (for example 1 AM from the afternoon) gets "not sure" for transit, never a guess.
A mapped bus stop alone is NOT treated as service running. The token is read from API_511_KEY and
never appears in messages. 511 allows about 60 requests per hour, so callers must cache.
"""
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from server.data.models import BoundingBox

BASE = "https://api.511.org/transit"
AGENCY = "SF"
STOPS_TTL_S = 24 * 3600


class TransitError(RuntimeError):
    """kind: not_configured | failed | timeout | rate_limited. Messages never contain the token."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class Arrival:
    stop_id: str
    line: str
    lat: float
    lng: float
    time: datetime


@dataclass(frozen=True)
class TransitSnapshot:
    arrivals: list[Arrival]
    fetched_at: datetime
    horizon: datetime          # we only know arrivals up to here

    def within(self, area: BoundingBox) -> "TransitSnapshot":
        keep = [a for a in self.arrivals
                if area.south <= a.lat <= area.north and area.west <= a.lng <= area.east]
        return TransitSnapshot(keep, self.fetched_at, self.horizon)


def _parse_time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def _json(resp: httpx.Response):
    return json.loads(resp.content.decode("utf-8-sig"))


def parse_stops(data: dict) -> dict[str, tuple[float, float]]:
    out = {}
    for p in data.get("Contents", {}).get("dataObjects", {}).get("ScheduledStopPoint", []):
        try:
            out[str(p["id"])] = (float(p["Location"]["Latitude"]), float(p["Location"]["Longitude"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def parse_arrivals(data: dict, stops: dict[str, tuple[float, float]], now: datetime,
                   horizon_min: int) -> list[Arrival]:
    visits = data.get("ServiceDelivery", {}).get("StopMonitoringDelivery", {}).get("MonitoredStopVisit", [])
    horizon = now + timedelta(minutes=horizon_min)
    out = []
    for v in visits:
        journey = v.get("MonitoredVehicleJourney", {})
        call = journey.get("MonitoredCall", {})
        stop_id = str(v.get("MonitoringRef") or call.get("StopPointRef") or "")
        when = _parse_time(call.get("ExpectedArrivalTime") or call.get("AimedArrivalTime"))
        if when is None or stop_id not in stops or when > horizon:
            continue
        lat, lng = stops[stop_id]
        out.append(Arrival(stop_id, str(journey.get("LineRef") or ""), lat, lng, when))
    return out


class Muni511Provider:
    def __init__(self, api_key: str | None = None, horizon_min: int = 30, timeout_s: float = 30.0,
                 client: httpx.Client | None = None):
        self._api_key = api_key
        self.horizon_min = horizon_min
        self.timeout_s = timeout_s
        self._client = client
        self._stops: dict[str, tuple[float, float]] | None = None
        self._stops_at = 0.0

    def _get(self, path: str, **params):
        key = self._api_key or os.environ.get("API_511_KEY")
        if not key:
            raise TransitError("not_configured", "API_511_KEY is not set")
        try:
            resp = (self._client or httpx).get(f"{BASE}/{path}", params={"api_key": key, "format": "json", **params},
                                               timeout=self.timeout_s)
        except httpx.TimeoutException:
            raise TransitError("timeout", "511 did not answer in time") from None
        except httpx.HTTPError:
            raise TransitError("failed", "511 could not be reached") from None
        if resp.status_code == 429:
            raise TransitError("rate_limited", "511 request limit reached")
        if resp.status_code != 200:
            raise TransitError("failed", f"511 answered HTTP {resp.status_code}")
        try:
            return _json(resp)
        except ValueError:
            raise TransitError("failed", "511 sent an unreadable answer") from None

    def _stop_locations(self) -> dict[str, tuple[float, float]]:
        if self._stops is None or time.monotonic() - self._stops_at > STOPS_TTL_S:
            self._stops = parse_stops(self._get("stops", operator_id=AGENCY))
            self._stops_at = time.monotonic()
        return self._stops

    def get_snapshot(self, now: datetime | None = None) -> TransitSnapshot:
        """Predicted arrivals for the whole agency in the next `horizon_min` minutes. Raises TransitError."""
        now = now or datetime.now(timezone.utc)
        stops = self._stop_locations()
        data = self._get("StopMonitoring", agency=AGENCY)
        return TransitSnapshot(parse_arrivals(data, stops, now, self.horizon_min), now,
                               now + timedelta(minutes=self.horizon_min))


class NoTransitProvider:
    """Used when no 511 token is configured. Always unknown."""

    def get_active_stops(self, area: BoundingBox, when: datetime):
        return None

    def get_snapshot(self, now: datetime | None = None):
        raise TransitError("not_configured", "no transit provider configured")
