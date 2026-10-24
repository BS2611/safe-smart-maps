"""Geometry and segmenter tests. Coordinates are [lng, lat] (GeoJSON order)."""
from datetime import datetime, timedelta, timezone

import pytest

from server.services.geo import (
    angle_between_deg,
    bearing_deg,
    cumulative_m,
    haversine_m,
    offset_point,
    point_at,
    point_to_polyline_m,
    point_to_segment_m,
)
from server.services.segmenter import segment_route

# ~1 km straight line going east at the latitude of San Francisco.
A = (-122.4484, 37.8029)
B = (-122.4370, 37.8029)
DEPART = datetime(2026, 10, 24, 22, 40, tzinfo=timezone.utc)


def test_haversine_known_distance():
    # One degree of latitude is about 111.2 km.
    assert haversine_m((0, 0), (0, 1)) == pytest.approx(111_195, rel=0.001)
    assert haversine_m(A, A) == 0


def test_cumulative_and_point_at():
    coords = [A, B]
    cum = cumulative_m(coords)
    assert cum[0] == 0 and cum[-1] == pytest.approx(haversine_m(A, B))
    mid = point_at(coords, cum, cum[-1] / 2)
    assert mid[0] == pytest.approx((A[0] + B[0]) / 2, abs=1e-6)
    assert point_at(coords, cum, -5) == A
    assert point_at(coords, cum, cum[-1] + 5) == B


def test_point_at_handles_repeated_points():
    coords = [A, A, B]
    cum = cumulative_m(coords)
    assert point_at(coords, cum, 1.0)[0] > A[0]


def test_bearing_and_angle():
    assert bearing_deg((0, 0), (0, 1)) == pytest.approx(0, abs=0.01)      # north
    assert bearing_deg((0, 0), (1, 0)) == pytest.approx(90, abs=0.01)     # east
    assert angle_between_deg(350, 10) == 20
    assert angle_between_deg(0, 180) == 180
    assert angle_between_deg(10, 350) == 20


def test_point_to_segment_distance():
    start, end = (-122.45, 37.80), (-122.44, 37.80)
    on_line = (-122.445, 37.80)
    assert point_to_segment_m(on_line, start, end) == pytest.approx(0, abs=0.5)
    north_100m = offset_point(on_line, 0, 100)
    assert point_to_segment_m(north_100m, start, end) == pytest.approx(100, abs=1.5)
    beyond = offset_point(end, 90, 50)
    assert point_to_segment_m(beyond, start, end) == pytest.approx(50, abs=1.5)
    assert point_to_segment_m(on_line, start, start) > 0   # zero-length segment


def test_point_to_polyline():
    line = [(-122.45, 37.80), (-122.44, 37.80), (-122.44, 37.81)]
    assert point_to_polyline_m((-122.44, 37.805), line) == pytest.approx(0, abs=0.5)
    assert point_to_polyline_m(line[0], [line[0]]) == 0


def test_offset_point_round_trip():
    p = offset_point(A, 90, 500)
    assert haversine_m(A, p) == pytest.approx(500, abs=1)


def test_segments_cover_whole_route_with_50m_target():
    segs = segment_route([A, B], DEPART, duration_s=900)
    total = haversine_m(A, B)
    assert segs[0].start_m == 0
    assert segs[-1].end_m == pytest.approx(total)
    assert all(abs(s.length_m - 50) < 5 for s in segs)
    assert [s.segment_id for s in segs][:2] == ["s0", "s1"]
    # continuity of positions
    for prev, cur in zip(segs, segs[1:], strict=False):
        assert prev.end_m == pytest.approx(cur.start_m)


def test_arrival_times_increase_and_end_near_duration():
    segs = segment_route([A, B], DEPART, duration_s=900)
    times = [s.arrival_time for s in segs]
    assert times == sorted(times)
    assert times[0] > DEPART
    assert times[-1] < DEPART + timedelta(seconds=900)
    assert (times[-1] - DEPART).total_seconds() > 850


def test_turn_angle_detected_at_corner():
    corner = (-122.4426, 37.8029)
    north = (-122.4426, 37.8100)
    segs = segment_route([A, corner, north], DEPART, duration_s=900)
    assert segs[0].turn_angle_deg == 0
    assert max(s.turn_angle_deg for s in segs) == pytest.approx(90, abs=15)


def test_short_route_is_one_segment():
    near = offset_point(A, 90, 20)
    segs = segment_route([A, near], DEPART, duration_s=15)
    assert len(segs) == 1


def test_segmenter_rejects_bad_input():
    with pytest.raises(ValueError, match="timezone-aware"):
        segment_route([A, B], datetime(2026, 10, 24, 22, 40), 100)
    with pytest.raises(ValueError, match="two coordinates"):
        segment_route([A], DEPART, 100)
    with pytest.raises(ValueError, match="zero length"):
        segment_route([A, A], DEPART, 100)
