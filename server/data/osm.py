"""OpenStreetMap context provider (Overpass API). No credentials needed.

Raw OSM tags are read ONLY in this file and converted to RoadContext / HelpPoint.
Public OSM data only. Missing or odd tags become "unknown", never a guess.
"""
import math
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from server.data.context import ContextProvider
from server.data.models import (
    ActivityPoint,
    AreaContext,
    BoundingBox,
    HelpPoint,
    RoadContext,
    StreetLamp,
)

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HELP_AMENITIES = ("police", "hospital", "fire_station")
# Busy places used only as a foot-traffic proxy. Not a count of people.
ACTIVITY_AMENITIES = (
    "cafe", "restaurant", "bar", "pub", "fast_food", "biergarten", "nightclub",
    "cinema", "theatre", "marketplace", "library", "university", "college",
)

# highway tag -> road_class. "_link" ramps map to their parent class.
_HIGHWAY_CLASS = {
    "motorway": "motorway", "trunk": "trunk", "primary": "primary", "secondary": "secondary",
    "tertiary": "tertiary",
    "residential": "residential", "living_street": "residential", "unclassified": "residential",
    "service": "service",
    "footway": "pedestrian", "pedestrian": "pedestrian", "path": "pedestrian",
    "steps": "pedestrian", "cycleway": "pedestrian",
}
# Only explicit tag values count as lit. Anything else (including "automatic", "limited") is unknown.
_LIT_YES = {"yes", "24/7", "sunset-sunrise"}
_LIT_NO = {"no"}
_DEDUPE_HELP_METERS = 100


class OsmError(RuntimeError):
    """Raised for upstream problems. Messages never contain credentials."""


def classify_highway(raw: Any) -> str:
    """Road class from an OSM `highway` value. Missing -> "unknown"; unlisted value -> "other"."""
    if not isinstance(raw, str) or not raw.strip():
        return "unknown"
    value = raw.strip().lower()
    if value.endswith("_link"):
        value = value[: -len("_link")]
    return _HIGHWAY_CLASS.get(value, "other")


def normalize_lit(raw: Any) -> str:
    """OSM `lit` -> "yes" | "no" | "unknown". A missing tag is unknown, NOT unlit."""
    if not isinstance(raw, str):
        return "unknown"
    value = raw.strip().lower()
    if value in _LIT_YES:
        return "yes"
    if value in _LIT_NO:
        return "no"
    return "unknown"


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def _osm_id(el: dict) -> int | None:
    return el["id"] if isinstance(el.get("id"), int) else None


def normalize_way(el: Any, fetched_at: datetime) -> RoadContext | None:
    """A way with a highway tag and at least 2 valid points, else None."""
    if not isinstance(el, dict) or el.get("type") != "way":
        return None
    tags = el.get("tags")
    if not isinstance(tags, dict) or not isinstance(tags.get("highway"), str) or not tags["highway"].strip():
        return None  # not a road
    points = []
    for p in el.get("geometry") or []:
        lat, lng = (_num(p.get("lat")), _num(p.get("lon"))) if isinstance(p, dict) else (None, None)
        if lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180:
            points.append((lat, lng))
    if len(points) < 2:
        return None
    name = tags.get("name")
    return RoadContext(
        coordinates=tuple(points), road_class=classify_highway(tags["highway"]),
        lit=normalize_lit(tags.get("lit")), source="osm", fetched_at=fetched_at,
        osm_id=_osm_id(el), name=name.strip() if isinstance(name, str) and name.strip() else None,
        raw_highway=tags["highway"].strip(),
        tunnel=str(tags.get("tunnel", "")).strip().lower() in {"yes", "building_passage"},
    )


def normalize_help_point(el: Any, fetched_at: datetime) -> HelpPoint | None:
    """A police / hospital / fire_station node or way (with `center`), else None."""
    if not isinstance(el, dict):
        return None
    tags = el.get("tags")
    kind = tags.get("amenity") if isinstance(tags, dict) else None
    if kind not in HELP_AMENITIES:
        return None
    where = el if el.get("type") == "node" else el.get("center")
    if not isinstance(where, dict):
        return None
    lat, lng = _num(where.get("lat")), _num(where.get("lon"))
    if lat is None or lng is None or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    name = tags.get("name")
    return HelpPoint(type=kind, lat=lat, lng=lng, source="osm", fetched_at=fetched_at,
                     name=name.strip() if isinstance(name, str) and name.strip() else None,
                     osm_id=_osm_id(el))


def _meters_apart(a: HelpPoint, b: HelpPoint) -> float:
    dy = (a.lat - b.lat) * 111_320
    dx = (a.lng - b.lng) * 111_320 * math.cos(math.radians(a.lat))
    return math.hypot(dx, dy)


def _point(el: dict) -> tuple[float, float] | None:
    where = el if el.get("type") == "node" else el.get("center")
    if not isinstance(where, dict):
        return None
    lat, lng = _num(where.get("lat")), _num(where.get("lon"))
    if lat is None or lng is None or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return lat, lng


def normalize_lamp(el: Any) -> StreetLamp | None:
    if not isinstance(el, dict) or el.get("type") != "node":
        return None
    tags = el.get("tags")
    if not isinstance(tags, dict) or tags.get("highway") != "street_lamp":
        return None
    point = _point(el)
    return None if point is None else StreetLamp(point[0], point[1], _osm_id(el))


def normalize_activity(el: Any) -> ActivityPoint | None:
    if not isinstance(el, dict):
        return None
    tags = el.get("tags")
    if not isinstance(tags, dict):
        return None
    kind = None
    shop = tags.get("shop")
    if isinstance(shop, str) and shop.strip() and shop.strip().lower() != "no":
        kind = "shop:" + shop.strip().lower()
    amenity = tags.get("amenity")
    if kind is None and isinstance(amenity, str) and amenity.strip().lower() in ACTIVITY_AMENITIES:
        kind = amenity.strip().lower()
    if kind is None:
        return None
    point = _point(el)
    return None if point is None else ActivityPoint(point[0], point[1], kind, _osm_id(el))


def normalize_elements(elements: Any, fetched_at: datetime) -> AreaContext:
    if not isinstance(elements, list):
        return AreaContext(roads=[], help_points=[], fetched_at=fetched_at, activity_known=False)
    roads, helps, lamps, busy, seen = [], [], [], [], set()
    for el in elements:
        if not isinstance(el, dict):
            continue
        key = (el.get("type"), el.get("id"))
        if el.get("id") is not None:
            if key in seen:
                continue
            seen.add(key)
        road = normalize_way(el, fetched_at)
        if road:
            roads.append(road)
        lamp = normalize_lamp(el)
        if lamp:
            lamps.append(lamp)
        busy_point = normalize_activity(el)
        if busy_point:
            busy.append(busy_point)
        hp = normalize_help_point(el, fetched_at)
        # a hospital mapped as both a node and a building way is one help point
        if hp and not any(h.type == hp.type and h.name == hp.name and _meters_apart(h, hp) < _DEDUPE_HELP_METERS
                          for h in helps):
            helps.append(hp)
    return AreaContext(roads=roads, help_points=helps, fetched_at=fetched_at,
                       street_lamps=lamps, activity_points=busy, activity_known=True)


def build_query(area: BoundingBox) -> str:
    bbox = f"{area.south},{area.west},{area.north},{area.east}"
    amenities = "|".join(HELP_AMENITIES)
    busy = "|".join(ACTIVITY_AMENITIES)
    return (f'[out:json][timeout:25];(way["highway"]({bbox});'
            f'node["highway"="street_lamp"]({bbox});'
            f'nwr["shop"]({bbox});'
            f'nwr["amenity"~"^({amenities}|{busy})$"]({bbox}););out tags geom center;')


class OverpassContextProvider(ContextProvider):
    def __init__(self, url: str | None = None, timeout_s: float = 40):
        self.url = url or os.environ.get("OVERPASS_URL") or DEFAULT_OVERPASS_URL
        self.timeout_s = timeout_s

    def get_area_context(self, area: BoundingBox) -> AreaContext:
        fetched_at = datetime.now(timezone.utc)
        try:
            resp = httpx.post(self.url, data={"data": build_query(area)}, timeout=self.timeout_s,
                              headers={"User-Agent": "safe-smart-maps-hackathon"})
        except httpx.HTTPError as e:
            raise OsmError(f"Overpass request failed: {type(e).__name__}") from e
        if resp.status_code != 200:
            raise OsmError(f"Overpass returned HTTP {resp.status_code}")
        try:
            body = resp.json()
        except ValueError as e:
            raise OsmError("Overpass returned unreadable JSON") from e
        if not isinstance(body, dict) or not isinstance(body.get("elements"), list):
            raise OsmError("Overpass response had no elements list")
        if "runtime error" in str(body.get("remark", "")).lower():
            raise OsmError("Overpass reported a runtime error (partial result discarded)")
        return normalize_elements(body["elements"], fetched_at)
