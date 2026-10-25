"""Candidate routes: Mapbox's own alternatives plus detours forced through a via point left and
right of the middle of the trip (TECHNICAL_SPEC 2.2 `candidates`). Walking requests often return a
single route, so without detours there would be nothing to compare.

The routing provider is injected (anything with `get_walking_routes(origin, dest, waypoints=())`
returning RouteCandidate), so tests use a fake. Points handed to the provider are (lng, lat); the
distance helpers here use (lat, lng) like geo.py.
"""
import math
from dataclasses import replace

from server.data.mapbox import PROVIDER, LngLat, MapboxError, RouteCandidate
from server.services.geo import EARTH_RADIUS_M, Point, haversine_m, point_to_polyline_m

MIN_REACH_M = 80.0


def bearing_deg(a: Point, b: Point) -> float:
    """Direction from a to b in degrees clockwise from north. Points are (lat, lng)."""
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlng = math.radians(b[1] - a[1])
    y = math.sin(dlng) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def offset_point(p: Point, bearing: float, distance_m: float) -> Point:
    """Point `distance_m` from p in direction `bearing`. Points are (lat, lng)."""
    ang = distance_m / EARTH_RADIUS_M
    brg = math.radians(bearing)
    lat1, lng1 = math.radians(p[0]), math.radians(p[1])
    lat2 = math.asin(math.sin(lat1) * math.cos(ang) + math.cos(lat1) * math.sin(ang) * math.cos(brg))
    lng2 = lng1 + math.atan2(math.sin(brg) * math.sin(ang) * math.cos(lat1),
                             math.cos(ang) - math.sin(lat1) * math.sin(lat2))
    return (math.degrees(lat2), math.degrees(lng2))


def detour_points(origin: LngLat, dest: LngLat, offset_m: float) -> list[LngLat]:
    """Two via points (left, then right of travel) near the middle of the trip, as (lng, lat)."""
    a, b = (origin[1], origin[0]), (dest[1], dest[0])
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    brg = bearing_deg(a, b)
    reach = min(offset_m, max(MIN_REACH_M, haversine_m(a, b) / 4))
    return [(lng, lat) for lat, lng in (offset_point(mid, brg - 90, reach),
                                        offset_point(mid, brg + 90, reach))]


def similar(a: RouteCandidate, b: RouteCandidate, tolerance_m: float, share: float) -> bool:
    """True if at least `share` of a's sampled points lie within tolerance of b, and vice versa."""
    def covered(x: RouteCandidate, y: RouteCandidate) -> float:
        xs, ys = x.as_lat_lng(), y.as_lat_lng()
        pts = xs[:: max(1, len(xs) // 25)]
        return sum(1 for p in pts if point_to_polyline_m(p, ys) <= tolerance_m) / len(pts)
    return covered(a, b) >= share and covered(b, a) >= share


def dedupe(candidates: list[RouteCandidate], cfg: dict) -> list[RouteCandidate]:
    """Drops near-identical routes, keeping the first (so Mapbox's own routes win over detours)."""
    c = cfg["candidates"]
    kept: list[RouteCandidate] = []
    for cand in candidates:
        if not any(similar(cand, k, c["dedupe_tolerance_m"], c["dedupe_share"]) for k in kept):
            kept.append(cand)
    return kept


def generate_candidates(routing, origin: LngLat, dest: LngLat, cfg: dict) -> list[RouteCandidate]:
    """Mapbox routes first, then detours. A failing detour is skipped; a failing main request raises
    MapboxError. Ids are renumbered mapbox-0.. across the merged list so they stay unique."""
    found = list(routing.get_walking_routes(origin, dest))
    for via in detour_points(origin, dest, cfg["candidates"]["detour_offset_m"]):
        try:
            found += routing.get_walking_routes(origin, dest, waypoints=[via])
        except MapboxError:
            continue
    unique = dedupe(found, cfg)
    return [replace(c, id=f"{PROVIDER}-{i}") for i, c in enumerate(unique)]
