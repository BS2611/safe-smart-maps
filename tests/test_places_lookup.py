"""Reading saved listings for a route's area from Amey's places cache. No network."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.data.models import BoundingBox
from server.services.places_lookup import places_for_area
from tests import fakes

ROUTE_AREA = BoundingBox(37.8019, -122.4494, 37.807, -122.439)


class PlacesLookupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_covering_entry_gives_places_and_data_time(self):
        provider = fakes.make_places_provider(self.dir, fakes.places())
        result = places_for_area(provider, ROUTE_AREA)
        self.assertEqual(len(result.places), len(fakes.places()))
        self.assertEqual(result.fetched_at, fakes.FETCHED)
        self.assertIsNone(result.warning)

    def test_nothing_saved_is_unavailable_not_empty(self):
        result = places_for_area(fakes.make_places_provider(self.dir), ROUTE_AREA)
        self.assertIsNone(result.places)
        self.assertIsNone(result.fetched_at)
        self.assertIn("not saved for this area", result.warning)

    def test_entry_for_somewhere_else_is_unavailable(self):
        elsewhere = BoundingBox(37.70, -122.40, 37.71, -122.39)
        provider = fakes.make_places_provider(self.dir, fakes.places(), area=elsewhere)
        self.assertIsNone(places_for_area(provider, ROUTE_AREA).places)

    def test_saved_empty_list_is_known_zero(self):
        result = places_for_area(fakes.make_places_provider(self.dir, []), ROUTE_AREA)
        self.assertEqual(result.places, [])
        self.assertIsNone(result.warning)

    def test_stale_entry_is_served_with_its_real_date_and_a_warning(self):
        old = datetime.now(timezone.utc) - timedelta(days=2)
        provider = fakes.make_places_provider(self.dir, fakes.places(), fetched_at=old, ttl_seconds=3600)
        result = places_for_area(provider, ROUTE_AREA)
        self.assertEqual(result.fetched_at, old)
        self.assertIn("older than 1 hours", result.warning)
        self.assertTrue(result.places)

    def test_partial_overlap_merges_entries_dedupes_and_warns(self):
        west = BoundingBox(37.80, -122.45, 37.81, -122.444)
        east = BoundingBox(37.80, -122.446, 37.81, -122.43)         # overlaps the west entry
        provider = fakes.make_places_provider(self.dir, fakes.places(), area=west)
        newer = fakes.FETCHED + timedelta(hours=1)
        fakes.make_places_provider(self.dir, fakes.places(), area=east, fetched_at=newer)
        # the second helper wrote into the same folder, so both entries now exist
        result = places_for_area(provider, ROUTE_AREA)
        ids = [p.place_id for p in result.places]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(result.fetched_at, fakes.FETCHED)           # the OLDEST entry time
        self.assertEqual(provider.lookup(ROUTE_AREA).status, "miss")     # no single entry covers it
        self.assertIn("only part", result.warning)

    def test_places_outside_the_route_area_are_left_out_on_partial_cover(self):
        wide_but_short = BoundingBox(37.80, -122.45, 37.8035, -122.43)   # does not reach the north
        provider = fakes.make_places_provider(self.dir, fakes.places(), area=wide_but_short)
        result = places_for_area(provider, ROUTE_AREA)
        self.assertIn("only part", result.warning)
        self.assertTrue(all(ROUTE_AREA.contains(p.lat, p.lng) for p in result.places))


if __name__ == "__main__":
    unittest.main()
