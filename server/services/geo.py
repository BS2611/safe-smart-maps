"""Small geographic helpers. Points are (lat, lng) in degrees; distances are meters."""
import math
from typing import Sequence

Point = tuple[float, float]
EARTH_RADIUS_M = 6_371_008.8


def haversine_m(a: Point, b: Point) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def interpolate(a: Point, b: Point, fraction: float) -> Point:
    """Point on the straight line a->b (fine at street scale)."""
    return (a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction)


def point_to_segment_m(p: Point, a: Point, b: Point) -> float:
    """Distance from p to the line piece a-b, using a local flat projection around p."""
    kx = math.cos(math.radians(p[0])) * math.pi / 180 * EARTH_RADIUS_M
    ky = math.pi / 180 * EARTH_RADIUS_M
    ax, ay = (a[1] - p[1]) * kx, (a[0] - p[0]) * ky
    bx, by = (b[1] - p[1]) * kx, (b[0] - p[0]) * ky
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / length_sq))
    return math.hypot(ax + t * dx, ay + t * dy)


def point_to_polyline_m(p: Point, line: Sequence[Point]) -> float:
    if not line:
        return math.inf
    if len(line) == 1:
        return haversine_m(p, line[0])
    return min(point_to_segment_m(p, line[i], line[i + 1]) for i in range(len(line) - 1))
