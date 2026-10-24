"""OpenStreetMap features via the Overpass API: street class, lit tag, tunnels, help points.

Public data, no key. Overpass requires a descriptive User-Agent (otherwise HTTP 406).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from server.data.errors import DataSourceError
from server.data.models import BoundingBox
from server.services.geo import LngLat

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
USER_AGENT = "safe-smart-maps-hackathon/0.1 (contact: bhavpreet.judge@sjsu.edu)"
LIT_YES = {"yes", "24/7", "automatic", "sunset-sunrise", "limited"}
HELP_KINDS = {"hospital", "police", "fire_station"}


@dataclass(frozen=True)
class Way:
    way_id: int
    highway: str | None
    lit: bool | None
    tunnel: bool
    name: str | None
    geometry: list[LngLat]


@dataclass(frozen=True)
class HelpPoint:
    name: str
    kind: str          # hospital | police | fire_station | store_24h
    lng: float
    lat: float
    source: str        # osm | brightdata


@dataclass(frozen=True)
class MapFeatures:
    ways: list[Way]
    help_points: list[HelpPoint]
    fetched_at: datetime


def build_query(area: BoundingBox) -> str:
    box = f"({area.south},{area.west},{area.north},{area.east})"
    return (
        "[out:json][timeout:55];"
        f'way["highway"]{box};out tags geom;'
        f'nwr["amenity"~"^(hospital|police|fire_station)$"]{box};out center tags;'
    )


def _lit(tag: str | None) -> bool | None:
    if tag is None:
        return None
    if tag in LIT_YES:
        return True
    if tag == "no":
        return False
    return None


def parse_overpass(payload: dict[str, Any], fetched_at: datetime) -> MapFeatures:
    ways: list[Way] = []
    help_points: list[HelpPoint] = []
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        if "highway" in tags and el.get("geometry"):
            geometry = [(p["lon"], p["lat"]) for p in el["geometry"] if "lat" in p and "lon" in p]
            if len(geometry) >= 1:
                layer = tags.get("layer")
                tunnel = tags.get("tunnel") in {"yes", "building_passage", "culvert"} or (
                    layer is not None and layer.lstrip("+").lstrip("-").isdigit() and layer.startswith("-"))
                ways.append(Way(el.get("id", 0), tags["highway"], _lit(tags.get("lit")),
                                bool(tunnel), tags.get("name"), geometry))
        elif tags.get("amenity") in HELP_KINDS:
            center = el.get("center") or {}
            lat = el.get("lat", center.get("lat"))
            lng = el.get("lon", center.get("lon"))
            if lat is not None and lng is not None:
                kind = tags["amenity"]
                help_points.append(HelpPoint(tags.get("name") or kind.replace("_", " ").title(),
                                             kind, lng, lat, "osm"))
    return MapFeatures(ways, help_points, fetched_at)


class OverpassProvider:
    """Tries each public Overpass server in turn: they are free and sometimes overloaded (HTTP 502/429)."""

    def __init__(self, urls: tuple[str, ...] = OVERPASS_URLS, timeout_s: float = 60.0,
                 client: httpx.Client | None = None):
        self.urls = urls
        self.timeout_s = timeout_s
        self._client = client

    def _post(self, url: str, area: BoundingBox) -> MapFeatures:
        try:
            resp = (self._client or httpx).post(url, data={"data": build_query(area)},
                                                headers={"User-Agent": USER_AGENT}, timeout=self.timeout_s)
        except httpx.TimeoutException:
            raise DataSourceError("osm", "request timed out", kind="timeout") from None
        except httpx.HTTPError as e:
            raise DataSourceError("osm", f"request failed ({type(e).__name__})") from None
        if resp.status_code != 200:
            raise DataSourceError("osm", f"HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except ValueError:
            raise DataSourceError("osm", "response was not valid JSON") from None
        return parse_overpass(payload, datetime.now(timezone.utc))

    def get_map_features(self, area: BoundingBox) -> MapFeatures:
        last: DataSourceError | None = None
        for url in self.urls:
            try:
                return self._post(url, area)
            except DataSourceError as e:
                last = e
        raise last or DataSourceError("osm", "no servers configured")
