"""Mapbox walking-route candidate provider (Directions API). Needs MAPBOX_TOKEN (server token).

Scope: start + destination -> Mapbox walking routes -> normalized RouteCandidate list. It does NOT
score, rank or label routes. Raw Mapbox JSON is read ONLY in this file.

COORDINATE ORDER: every coordinate in this file is (longitude, latitude), the same order Mapbox and
GeoJSON use. The rest of the backend (geo.py, segmenter) uses (lat, lng): call
`RouteCandidate.as_lat_lng()` when handing a route to it, never swap by hand.
"""
import math
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/walking"
PROVIDER = "mapbox"

LngLat = tuple[float, float]


class MapboxError(RuntimeError):
    """Mapbox could not deliver routes. Messages never contain the token, URL or user coordinates.

    `kind`: failed | timeout | not_configured | empty
    """

    def __init__(self, message: str, kind: str = "failed"):
        super().__init__(f"mapbox: {message}")
        self.kind = kind


@dataclass(frozen=True)
class RouteCandidate:
    """One walking route, as Mapbox proposed it. No scores, no safety claims.

    id:          "mapbox-<n>", n = position in Mapbox's answer (0 = Mapbox's preferred route).
                 Stable within one response; a dropped bad route leaves a gap, ids never shift.
    coordinates: ordered path start -> destination as (longitude, latitude).
    distance_m:  total walking distance in meters.
    duration_s:  Mapbox's estimated walking time in seconds.
    """
    id: str
    provider: str
    coordinates: list[LngLat]
    distance_m: float
    duration_s: float

    def as_lat_lng(self) -> list[tuple[float, float]]:
        """Same path as (lat, lng) points: the order geo.py and the segmenter expect."""
        return [(lat, lng) for lng, lat in self.coordinates]


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _valid_lng_lat(lng: Any, lat: Any) -> LngLat | None:
    lng, lat = _finite_number(lng), _finite_number(lat)
    if lng is None or lat is None or not -180 <= lng <= 180 or not -90 <= lat <= 90:
        return None
    return (lng, lat)


def check_point(point: Any, name: str) -> LngLat:
    """Validates a caller-supplied (lng, lat). A swapped (lat, lng) pair fails here when lat > 90."""
    if not isinstance(point, (tuple, list)) or len(point) != 2:
        raise ValueError(f"{name} must be a (longitude, latitude) pair")
    checked = _valid_lng_lat(point[0], point[1])
    if checked is None:
        raise ValueError(f"{name} must be a valid (longitude, latitude): longitude -180..180, latitude -90..90")
    return checked


def _normalize_route(raw: Any, index: int) -> RouteCandidate | None:
    """None when this route cannot be used (missing/short/odd geometry, bad distance or duration)."""
    if not isinstance(raw, dict):
        return None
    geometry = raw.get("geometry")
    points = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(points, list) or len(points) < 2:
        return None
    coordinates: list[LngLat] = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            return None
        checked = _valid_lng_lat(p[0], p[1])
        if checked is None:
            return None
        coordinates.append(checked)
    distance, duration = _finite_number(raw.get("distance")), _finite_number(raw.get("duration"))
    if distance is None or duration is None or distance <= 0 or duration <= 0:
        return None
    return RouteCandidate(f"{PROVIDER}-{index}", PROVIDER, coordinates, distance, duration)


def _safe_code(payload: dict) -> str:
    code = payload.get("code")
    return code if isinstance(code, str) and re.fullmatch(r"[A-Za-z]{1,30}", code) else ""


def parse_directions(payload: Any) -> list[RouteCandidate]:
    """Directions API answer -> usable routes in Mapbox order.

    No routes at all -> MapboxError(kind="empty"). Routes present but none usable -> kind="failed".
    A bad route next to good ones is dropped; unknown vendor fields are ignored.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("routes"), list):
        raise MapboxError("response had an unexpected shape")
    raw_routes = payload["routes"]
    if not raw_routes:
        code = _safe_code(payload)
        raise MapboxError("no walking route found between these points" + (f" ({code})" if code else ""),
                          kind="empty")
    routes = [r for i, raw in enumerate(raw_routes) if (r := _normalize_route(raw, i)) is not None]
    if not routes:
        raise MapboxError("no usable route geometry in the response")
    return routes


class MapboxWalkingProvider:
    def __init__(self, token: str | None = None, timeout_s: float = 12.0,
                 client: httpx.Client | None = None):
        self._token = token
        self.timeout_s = timeout_s
        self._client = client

    @property
    def token(self) -> str:
        token = (self._token or os.environ.get("MAPBOX_TOKEN") or "").strip()
        if not token:
            raise MapboxError("MAPBOX_TOKEN is not set", kind="not_configured")
        return token

    def get_walking_routes(self, origin: LngLat, dest: LngLat) -> list[RouteCandidate]:
        """Walking routes from `origin` to `dest`, both (longitude, latitude).

        Asks Mapbox for alternatives; returns what it sent, in its order. Raises ValueError for
        invalid points and MapboxError (see `kind`) for everything else.
        """
        start, end = check_point(origin, "origin"), check_point(dest, "dest")
        token = self.token  # checked before any network call
        path = ";".join(f"{lng:.6f},{lat:.6f}" for lng, lat in (start, end))
        params = {"alternatives": "true", "geometries": "geojson", "overview": "full",
                  "steps": "false", "access_token": token}
        try:
            resp = (self._client or httpx).get(f"{DIRECTIONS_URL}/{path}", params=params,
                                               timeout=self.timeout_s)
        except httpx.TimeoutException:
            raise MapboxError("request timed out", kind="timeout") from None
        except httpx.HTTPError as e:
            # Never str(e): httpx errors can carry the request URL, which contains the token.
            raise MapboxError(f"request failed ({type(e).__name__})") from None
        if resp.status_code != 200:
            raise MapboxError(f"HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except ValueError:
            raise MapboxError("response was not valid JSON") from None
        return parse_directions(payload)
