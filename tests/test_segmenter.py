"""Segmenter tests. Coordinates are synthetic TEST FIXTURES."""
import unittest

from server.services.geo import haversine_m
from server.services.segmenter import join_legs, segment_route

M = 1 / 111_195          # degrees of latitude per meter (approx)
LNG = -122.45


def line(*meters):
    """North-going route through the given cumulative meter marks (lat, lng)."""
    return [(37.8 + m * M, LNG) for m in meters]


def route_len(coords):
    return sum(haversine_m(a, b) for a, b in zip(coords, coords[1:]))


class SegmenterTests(unittest.TestCase):
    def test_short_route_is_one_segment(self):
        segs = segment_route(line(0, 20))
        self.assertEqual(len(segs), 1)
        self.assertAlmostEqual(segs[0].length_m, 20, delta=0.1)

    def test_about_50m(self):
        segs = segment_route(line(0, 50))
        self.assertEqual(len(segs), 1)
        self.assertAlmostEqual(segs[0].length_m, 50, delta=0.1)

    def test_longer_route_splits_evenly(self):
        segs = segment_route(line(0, 230))        # round(4.6) = 5 segments of ~46 m
        self.assertEqual(len(segs), 5)
        for s in segs:
            self.assertAlmostEqual(s.length_m, 46, delta=0.2)
            self.assertTrue(25 <= s.length_m <= 75)

    def test_multi_edge_keeps_inner_vertices(self):
        coords = [(37.8, LNG), (37.8 + 60 * M, LNG), (37.8 + 60 * M, LNG + 80 * M * 1.26)]
        segs = segment_route(coords, 50)
        total = route_len(coords)
        self.assertAlmostEqual(sum(s.length_m for s in segs), total, delta=0.1)
        all_pts = {p for s in segs for p in s.coordinates}
        self.assertIn(coords[1], all_pts)

    def test_repeated_coordinate_ignored(self):
        a = segment_route(line(0, 100))
        b = segment_route([line(0)[0], line(0)[0], *line(100)])
        self.assertEqual(len(a), len(b))
        self.assertAlmostEqual(a[0].length_m, b[0].length_m, places=6)

    def test_zero_length_edge_in_middle(self):
        c = line(0, 60)
        segs = segment_route([c[0], c[1], c[1], (c[1][0] + 60 * M, LNG)])
        self.assertAlmostEqual(sum(s.length_m for s in segs), 120, delta=0.2)

    def test_degenerate_inputs(self):
        self.assertEqual(segment_route([]), [])
        self.assertEqual(segment_route([(37.8, LNG)]), [])
        self.assertEqual(segment_route([(37.8, LNG), (37.8, LNG)]), [])

    def test_total_length_and_order_preserved(self):
        coords = [(37.8, LNG), (37.8007, LNG + 0.0003), (37.8015, LNG + 0.0003), (37.8015, LNG + 0.001)]
        segs = segment_route(coords)
        self.assertAlmostEqual(sum(s.length_m for s in segs), route_len(coords), delta=0.1)
        self.assertEqual(segs[0].start, coords[0])
        self.assertEqual(segs[-1].end, coords[-1])
        for prev, nxt in zip(segs, segs[1:]):
            self.assertEqual(prev.end, nxt.start)
            self.assertAlmostEqual(nxt.offset_m, prev.offset_m + prev.length_m, places=6)
        self.assertEqual([s.index for s in segs], list(range(len(segs))))
        # geometry of each segment is as long as the segment says
        for s in segs:
            self.assertAlmostEqual(route_len(s.coordinates), s.length_m, delta=0.2)

    def test_midpoint_is_halfway(self):
        s = segment_route(line(0, 40))[0]
        self.assertAlmostEqual(haversine_m(s.start, s.midpoint), 20, delta=0.2)

    def test_join_legs(self):
        legs = [line(0, 40), line(40, 80)]
        segs = segment_route(join_legs(legs))        # shared joint point is a repeat, dropped
        self.assertAlmostEqual(sum(s.length_m for s in segs), 80, delta=0.2)


if __name__ == "__main__":
    unittest.main()
