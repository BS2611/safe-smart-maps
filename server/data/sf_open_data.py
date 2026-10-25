"""San Francisco open data (Socrata, public, no key): open streetlight 311 reports and incidents.

The planner calls this. A failed request becomes a warning and a null factor. Fields are
named lat / lng. Incident data stays at a low weight: it reflects policing as much as events.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from server.data.models import BoundingBox

BASE = "https://data.sf.gov/resource"
CASES_311 = "vw6y-z8j6"
INCIDENTS = "wg3w-h783"
USER_AGENT = "safe-smart-maps-hackathon/0.1"


class SfDataError(RuntimeError):
    """SF open data could not deliver. Messages never contain coordinates. `kind`: failed | timeout."""

    def __init__(self, source: str, message: str, kind: str = "failed"):
        super().__init__(f"{source}: {message}")
        self.source = source
        self.kind = kind


@dataclass(frozen=True)
class Outage:
    lng: float
    lat: float
    reported_at: str


@dataclass(frozen=True)
class Incident:
    lng: float
    lat: float
    category: str


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_outages(rows: list[dict]) -> list[Outage]:
    out = []
    for r in rows:
        lat, lng = _num(r.get("lat")), _num(r.get("long"))
        if lat is not None and lng is not None:
            out.append(Outage(lng, lat, str(r.get("requested_datetime", ""))))
    return out


def parse_incidents(rows: list[dict]) -> list[Incident]:
    out = []
    for r in rows:
        lat, lng = _num(r.get("latitude")), _num(r.get("longitude"))
        if lat is not None and lng is not None:
            out.append(Incident(lng, lat, str(r.get("incident_category", ""))))
    return out


def _box(area: BoundingBox, field: str) -> str:
    return f"within_box({field}, {area.north}, {area.west}, {area.south}, {area.east})"


class SocrataClient:
    def __init__(self, timeout_s: float = 20.0, client: httpx.Client | None = None):
        self.timeout_s = timeout_s
        self._client = client

    def _get(self, dataset: str, params: dict[str, Any], source: str) -> list[dict]:
        url = f"{BASE}/{dataset}.json"
        headers = {"User-Agent": USER_AGENT}
        try:
            if self._client is not None:
                resp = self._client.get(url, params=params, headers=headers, timeout=self.timeout_s)
            else:
                resp = httpx.get(url, params=params, headers=headers, timeout=self.timeout_s,
                                 follow_redirects=True)
        except httpx.TimeoutException:
            raise SfDataError(source, "request timed out", kind="timeout") from None
        except httpx.HTTPError as e:
            raise SfDataError(source, f"request failed ({type(e).__name__})") from None
        if resp.status_code != 200:
            raise SfDataError(source, f"HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            raise SfDataError(source, "response was not valid JSON") from None
        if not isinstance(data, list):
            raise SfDataError(source, "unexpected response shape")
        return data

    def get_open_outages(self, area: BoundingBox) -> list[Outage]:
        where = f"service_name = 'Streetlights' AND status_description = 'Open' AND {_box(area, 'point_geom')}"
        rows = self._get(CASES_311, {"$where": where, "$limit": 500}, "sf311")
        return parse_outages(rows)

    def get_recent_incidents(self, area: BoundingBox, now: datetime | None = None,
                             days: int = 90) -> list[Incident]:
        since = ((now or datetime.now(timezone.utc)) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00")
        where = f"incident_datetime > '{since}' AND {_box(area, 'point')}"
        rows = self._get(INCIDENTS, {"$where": where, "$limit": 2000}, "sf_incidents")
        return parse_incidents(rows)

