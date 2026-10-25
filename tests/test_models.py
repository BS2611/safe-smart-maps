"""BoundingBox / Place model tests. Pure unit tests; values are hand-written TEST FIXTURES."""
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

from server.data.models import BoundingBox, Place

FETCHED = datetime(2026, 10, 24, tzinfo=timezone.utc)
BOX = BoundingBox(south=37.70, west=-122.50, north=37.80, east=-122.40)


class BoundingBoxTests(unittest.TestCase):
    def test_inside(self):
        self.assertTrue(BOX.contains(37.75, -122.45))

    def test_edges_and_corners_are_inside(self):
        for lat, lng in [(37.70, -122.50), (37.80, -122.40), (37.70, -122.40), (37.80, -122.50),
                         (37.75, -122.50), (37.70, -122.45)]:
            self.assertTrue(BOX.contains(lat, lng), (lat, lng))

    def test_just_outside_each_side(self):
        eps = 1e-6
        for lat, lng in [(37.70 - eps, -122.45), (37.80 + eps, -122.45),
                         (37.75, -122.50 - eps), (37.75, -122.40 + eps)]:
            self.assertFalse(BOX.contains(lat, lng), (lat, lng))

    def test_far_outside(self):
        self.assertFalse(BOX.contains(0.0, 0.0))

    def test_center(self):
        lat, lng = BOX.center
        self.assertAlmostEqual(lat, 37.75)
        self.assertAlmostEqual(lng, -122.45)

    def test_is_immutable_and_comparable(self):
        with self.assertRaises(FrozenInstanceError):
            BOX.south = 0
        self.assertEqual(BOX, BoundingBox(37.70, -122.50, 37.80, -122.40))

    def test_inverted_box_contains_nothing(self):
        # Current design: no validation in the constructor. An inverted box is empty, not an error.
        inverted = BoundingBox(south=37.80, west=-122.40, north=37.70, east=-122.50)
        self.assertFalse(inverted.contains(37.75, -122.45))

    def test_nan_is_never_contained(self):
        self.assertFalse(BOX.contains(float("nan"), -122.45))


class PlaceTests(unittest.TestCase):
    def test_required_fields_and_defaults(self):
        p = Place("A", 1.0, 2.0, "cafe", "fixture", FETCHED, None, None)
        self.assertIsNone(p.place_id)
        self.assertIsNone(p.raw_category)
        self.assertIsNone(p.weekly_hours)

    def test_missing_required_field_raises(self):
        with self.assertRaises(TypeError):
            Place(name="A", lat=1.0, lng=2.0)  # type: ignore[call-arg]

    def test_is_immutable(self):
        p = Place("A", 1.0, 2.0, "cafe", "fixture", FETCHED, None, None)
        with self.assertRaises(FrozenInstanceError):
            p.name = "B"
