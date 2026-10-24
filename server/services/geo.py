"""Small geometry helpers on [lng, lat] coordinates. Pure functions, no network."""
import math

EARTH_RADIUS_M = 6_371_000.0

LngLat = tuple[float, float]


def haversine_m(a: LngLat, b: LngLat) -> float:
    lat1, lat2 = math.radians(a[1]), math.radians(b[1])
    dlat = lat2 - lat1
    dlng = math.radians(b[0] - a[0])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def cumulative_m(coords: list[LngLat]) -> list[float]:
    """Distance from the start to each coordinate."""
    out = [0.0]
    for prev, cur in zip(coords, coords[1:], strict=False):
        out.append(out[-1] + haversine_m(prev, cur))
    return out


def point_at(coords: list[LngLat], cum: list[float], distance_m: float) -> LngLat:
    """Point `distance_m` along the polyline (clamped to its ends)."""
    if distance_m <= 0:
        return coords[0]
    if distance_m >= cum[-1]:
        return coords[-1]
    for i in range(1, len(cum)):
        if cum[i] >= distance_m:
            span = cum[i] - cum[i - 1]
            t = 0.0 if span == 0 else (distance_m - cum[i - 1]) / span
            a, b = coords[i - 1], coords[i]
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return coords[-1]  # pragma: no cover


def bearing_deg(a: LngLat, b: LngLat) -> float:
    lat1, lat2 = math.radians(a[1]), math.radians(b[1])
    dlng = math.radians(b[0] - a[0])
    y = math.sin(dlng) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def angle_between_deg(b1: float, b2: float) -> float:
    """Smallest turn angle between two bearings, 0..180."""
    diff = abs(b1 - b2) % 360
    return 360 - diff if diff > 180 else diff


def _to_xy(p: LngLat, ref_lat: float) -> tuple[float, float]:
    x = math.radians(p[0]) * math.cos(math.radians(ref_lat)) * EARTH_RADIUS_M
    y = math.radians(p[1]) * EARTH_RADIUS_M
    return x, y


def point_to_segment_m(p: LngLat, a: LngLat, b: LngLat) -> float:
    """Distance in metres from p to the segment a-b (local flat approximation)."""
    ref = p[1]
    px, py = _to_xy(p, ref)
    ax, ay = _to_xy(a, ref)
    bx, by = _to_xy(b, ref)
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def point_to_polyline_m(p: LngLat, line: list[LngLat]) -> float:
    if len(line) == 1:
        return haversine_m(p, line[0])
    return min(point_to_segment_m(p, a, b) for a, b in zip(line, line[1:], strict=False))


def offset_point(p: LngLat, bearing: float, distance_m: float) -> LngLat:
    """Point `distance_m` from p in the direction `bearing` (degrees from north)."""
    ang = distance_m / EARTH_RADIUS_M
    brg = math.radians(bearing)
    lat1, lng1 = math.radians(p[1]), math.radians(p[0])
    lat2 = math.asin(math.sin(lat1) * math.cos(ang) + math.cos(lat1) * math.sin(ang) * math.cos(brg))
    lng2 = lng1 + math.atan2(
        math.sin(brg) * math.sin(ang) * math.cos(lat1),
        math.cos(ang) - math.sin(lat1) * math.sin(lat2),
    )
    return (math.degrees(lng2), math.degrees(lat2))
