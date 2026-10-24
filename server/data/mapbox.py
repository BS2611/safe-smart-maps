"""Mapbox Directions (walking) routing provider. Needs MAPBOX_TOKEN (server token, from env only).

Candidate routes: the request with alternatives, plus detours forced through a via point placed
to the left and right of the middle of the trip (TECHNICAL_SPEC section 2.2).
"""
import hashlib
import os
from dataclasses import dataclass
from typing import Any

import httpx

from server.data.errors import DataSourceError, NotConfiguredError
from server.services.geo import LngLat, bearing_deg, haversine_m, offset_point, point_to_polyline_m

DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/walking"


@dataclass(frozen=True)
class Step:
    name: str
    distance_m: float


@dataclass(frozen=True)
class RouteCandidate:
    route_id: str
    coords: list[LngLat]
    distance_m: float
    duration_s: float
    steps: list[Step]

    def via(self, count: int = 2) -> list[str]:
        """Names of the longest named steps, in route order (e.g. ["Polk St", "Market St"])."""
        named: dict[str, float] = {}
        for s in self.steps:
            if s.name:
                named[s.name] = named.get(s.name, 0.0) + s.distance_m
        top = sorted(named, key=lambda n: -named[n])[:count]
        order = [s.name for s in self.steps if s.name in top]
        seen: list[str] = []
        for n in order:
            if n not in seen:
                seen.append(n)
        return seen


def make_route_id(coords: list[LngLat]) -> str:
    sample = coords[:: max(1, len(coords) // 12)] + [coords[-1]]
    text = ";".join(f"{lng:.4f},{lat:.4f}" for lng, lat in sample)
    return "r" + hashlib.sha1(text.encode()).hexdigest()[:10]


def parse_directions(payload: dict[str, Any]) -> list[RouteCandidate]:
    out = []
    for r in payload.get("routes", []):
        coords = [(float(c[0]), float(c[1])) for c in (r.get("geometry") or {}).get("coordinates", [])]
        if len(coords) < 2 or not r.get("distance") or not r.get("duration"):
            continue
        steps = [Step(s.get("name") or "", float(s.get("distance", 0)))
                 for leg in r.get("legs", []) for s in leg.get("steps", [])]
        out.append(RouteCandidate(make_route_id(coords), coords, float(r["distance"]),
                                  float(r["duration"]), steps))
    return out


def similar(a: RouteCandidate, b: RouteCandidate, tolerance_m: float = 20.0,
            share: float = 0.9) -> bool:
    """True if at least `share` of a's sampled points lie within tolerance of b (and vice versa)."""
    def covered(x: RouteCandidate, y: RouteCandidate) -> float:
        pts = x.coords[:: max(1, len(x.coords) // 25)]
        near = sum(1 for p in pts if point_to_polyline_m(p, y.coords) <= tolerance_m)
        return near / len(pts)
    return covered(a, b) >= share and covered(b, a) >= share


def dedupe(cands: list[RouteCandidate]) -> list[RouteCandidate]:
    kept: list[RouteCandidate] = []
    for c in cands:
        if not any(similar(c, k) for k in kept):
            kept.append(c)
    return kept


def detour_points(origin: LngLat, dest: LngLat, offset_m: float = 250.0) -> list[LngLat]:
    """Via points left and right of the middle of the trip, used to force alternative streets."""
    mid = ((origin[0] + dest[0]) / 2, (origin[1] + dest[1]) / 2)
    brg = bearing_deg(origin, dest)
    reach = min(offset_m, max(80.0, haversine_m(origin, dest) / 4))
    return [offset_point(mid, brg - 90, reach), offset_point(mid, brg + 90, reach)]


class MapboxRoutingProvider:
    def __init__(self, token: str | None = None, timeout_s: float = 12.0,
                 client: httpx.Client | None = None):
        self._token = token
        self.timeout_s = timeout_s
        self._client = client

    @property
    def token(self) -> str:
        token = self._token or os.environ.get("MAPBOX_TOKEN")
        if not token:
            raise NotConfiguredError("mapbox", "MAPBOX_TOKEN")
        return token

    def _directions(self, points: list[LngLat], alternatives: bool) -> list[RouteCandidate]:
        coords = ";".join(f"{lng:.6f},{lat:.6f}" for lng, lat in points)
        params = {"alternatives": str(alternatives).lower(), "geometries": "geojson",
                  "overview": "full", "steps": "true", "access_token": self.token}
        url = f"{DIRECTIONS_URL}/{coords}"
        try:
            resp = (self._client or httpx).get(url, params=params, timeout=self.timeout_s)
        except httpx.TimeoutException:
            raise DataSourceError("mapbox", "request timed out", kind="timeout") from None
        except httpx.HTTPError as e:
            raise DataSourceError("mapbox", f"request failed ({type(e).__name__})") from None
        if resp.status_code != 200:
            # The body can echo the request URL, so never include it in the message.
            raise DataSourceError("mapbox", f"HTTP {resp.status_code}")
        try:
            return parse_directions(resp.json())
        except ValueError:
            raise DataSourceError("mapbox", "response was not valid JSON") from None

    def get_walking_routes(self, origin: LngLat, dest: LngLat) -> list[RouteCandidate]:
        """Main routes first, then detours. Individual detour failures are ignored; the main
        request failing raises. Near-duplicate routes are removed."""
        candidates = self._directions([origin, dest], alternatives=True)
        for via in detour_points(origin, dest):
            try:
                candidates += self._directions([origin, via, dest], alternatives=False)
            except DataSourceError:
                continue
        return dedupe(candidates)
