"""Splits a route into ~50 m segments and estimates when the walker reaches each one."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from server.services.geo import (
    LngLat,
    angle_between_deg,
    bearing_deg,
    cumulative_m,
    point_at,
)


@dataclass(frozen=True)
class Segment:
    index: int
    start: LngLat
    end: LngLat
    mid: LngLat
    start_m: float
    end_m: float
    arrival_time: datetime
    turn_angle_deg: float  # angle between this segment's direction and the previous one

    @property
    def length_m(self) -> float:
        return self.end_m - self.start_m

    @property
    def segment_id(self) -> str:
        return f"s{self.index}"


def segment_route(
    coords: list[LngLat],
    depart_at: datetime,
    duration_s: float,
    target_m: float = 50.0,
) -> list[Segment]:
    """Equal-length segments close to `target_m`. Arrival time is at each segment's middle,
    assuming a constant walking pace over the whole route (duration_s / total length)."""
    if depart_at.tzinfo is None:
        raise ValueError("depart_at must be timezone-aware")
    if len(coords) < 2:
        raise ValueError("a route needs at least two coordinates")
    cum = cumulative_m(coords)
    total = cum[-1]
    if total <= 0:
        raise ValueError("route has zero length")
    count = max(1, round(total / target_m))
    step = total / count
    segments: list[Segment] = []
    prev_bearing: float | None = None
    for i in range(count):
        d0, d1 = i * step, (i + 1) * step
        start, end = point_at(coords, cum, d0), point_at(coords, cum, d1)
        mid = point_at(coords, cum, (d0 + d1) / 2)
        brg = bearing_deg(start, end)
        turn = 0.0 if prev_bearing is None else angle_between_deg(prev_bearing, brg)
        prev_bearing = brg
        arrival = depart_at + timedelta(seconds=duration_s * ((d0 + d1) / 2) / total)
        segments.append(Segment(i, start, end, mid, d0, d1, arrival, turn))
    return segments
