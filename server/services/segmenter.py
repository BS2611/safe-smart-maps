"""Splits a walking route into ~fixed-length segments. Independent of any routing provider.

Algorithm: drop repeated points, measure the polyline with haversine, then cut it into
n = max(1, round(length / target)) EQUAL pieces (so no tiny leftover piece and every segment
is within about +-50% of the target; routes shorter than the target give one segment).
Cuts can fall inside an original edge; the original vertices inside a piece are kept so the
geometry follows the route exactly.
"""
import bisect
from dataclasses import dataclass

from server.services.geo import Point, haversine_m, interpolate


@dataclass(frozen=True)
class Segment:
    index: int
    segment_id: str
    start: Point                        # (lat, lng)
    end: Point
    midpoint: Point                     # halfway ALONG the segment's path
    length_m: float
    coordinates: tuple[Point, ...]      # start, any original vertices inside, end
    offset_m: float                     # distance from the route start to this segment's start


def join_legs(legs: list[list[Point]]) -> list[Point]:
    """Concatenate multi-leg polylines into one ordered list (a repeated joint point is dropped later)."""
    return [p for leg in legs for p in leg]


def _dedupe(coords: list[Point]) -> list[Point]:
    out: list[Point] = []
    for p in coords:
        if not out or haversine_m(out[-1], p) > 0:
            out.append((float(p[0]), float(p[1])))
    return out


def segment_route(coords: list[Point], target_m: float = 50.0) -> list[Segment]:
    """Ordered (lat, lng) route points -> ordered segments. Fewer than two distinct points -> []."""
    pts = _dedupe(list(coords))
    if len(pts) < 2:
        return []
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + haversine_m(a, b))
    total = cum[-1]

    def point_at(d: float) -> Point:
        d = max(0.0, min(total, d))
        i = min(bisect.bisect_right(cum, d) - 1, len(pts) - 2)
        edge = cum[i + 1] - cum[i]
        return interpolate(pts[i], pts[i + 1], 0.0 if edge == 0 else (d - cum[i]) / edge)

    n = max(1, round(total / target_m))
    step = total / n
    segments = []
    for k in range(n):
        a, b = k * step, (k + 1) * step
        start = pts[0] if k == 0 else point_at(a)
        end = pts[-1] if k == n - 1 else point_at(b)
        inner = [pts[i] for i in range(len(pts)) if a < cum[i] < b]
        segments.append(Segment(
            index=k, segment_id=f"seg-{k}", start=start, end=end, midpoint=point_at(a + step / 2),
            length_m=step, coordinates=(start, *inner, end), offset_m=a))
    return segments
