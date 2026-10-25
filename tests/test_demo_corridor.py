"""Demo corridor, labeled fixtures only: Palace of Fine Arts to Montgomery BART, 8 PM vs 1 AM.

This does not call Bright Data, Mapbox, Overpass, or SF open data. The GTFS files in
tests/fixtures/gtfs_demo are a labeled fixture, not a live feed.
"""
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from server.data.gtfs import load_gtfs
from server.data.models import ActivityPoint, AreaContext, Place, RoadContext, StreetLamp
from server.data.sf_open_data import Incident
from server.services.scoring_config import load_scoring_config
from server.services.segment_scoring import SegmentScorer
from server.services.segmenter import segment_route

PT = ZoneInfo("America/Los_Angeles")
EIGHT_PM = datetime(2026, 10, 24, 20, 0, tzinfo=PT)
ONE_AM = datetime(2026, 10, 25, 1, 0, tzinfo=PT)
FETCHED = datetime(2026, 10, 24, 18, 0, tzinfo=PT)
PALACE = (37.8029, -122.4484)
BEND = (37.8100, -122.4300)
MONTGOMERY = (37.7894, -122.4013)
CFG = load_scoring_config()


def corridor_segments():
    return segment_route([PALACE, BEND, MONTGOMERY], CFG["segment_length_m"])


def context():
    fetched = datetime(2026, 10, 24, 18, 0, tzinfo=PT)
    road = RoadContext(coordinates=(PALACE, BEND, MONTGOMERY), road_class="secondary", lit="unknown",
                       source="test-fixture", fetched_at=fetched, name="demo corridor")
    return AreaContext(
        roads=[road], help_points=[], fetched_at=fetched,
        street_lamps=[StreetLamp(*PALACE)],
        activity_points=[ActivityPoint(*PALACE, "cafe"), ActivityPoint(PALACE[0], PALACE[1] + 0.0002, "restaurant")],
        activity_known=True)


class DemoCorridorTests(unittest.TestCase):
    def setUp(self):
        self.segments = corridor_segments()
        self.schedule = load_gtfs(Path(__file__).parent / "fixtures" / "gtfs_demo")
        self.places = [Place(
            name="Cafe near the Palace", lat=PALACE[0], lng=PALACE[1] + 0.00015, category="cafe",
            source="test-fixture", fetched_at=FETCHED,
            weekly_hours={d: [(17 * 60, 23 * 60)] for d in range(7)}, is_24h=None)]
        self.incidents = [Incident(BEND[1], BEND[0], "test-fixture")]

    def score(self, when):
        scorer = SegmentScorer(CFG, self.places, context(), incidents=self.incidents, transit=self.schedule)
        return scorer.score_route(self.segments, when)

    def test_feed_has_an_evening_departure_only(self):
        self.assertEqual(len(self.schedule.active_stops(EIGHT_PM, 15)), 1)
        self.assertEqual(self.schedule.active_stops(ONE_AM, 15), [])

    def test_each_factor_is_real_and_the_late_walk_scores_lower(self):
        early = self.score(EIGHT_PM)
        late = self.score(ONE_AM)
        start, end = early[0], early[-1]
        self.assertGreater(start.factors["open_places"].value, late[0].factors["open_places"].value)
        self.assertGreater(start.factors["activity"].value, late[0].factors["activity"].value)
        self.assertIn("estimate", start.factors["activity"].reason)
        self.assertGreater(start.factors["lighting"].value, 0)
        self.assertIsNone(end.factors["lighting"].value)
        self.assertEqual(start.factors["transit"].value, 0)
        self.assertGreater(end.factors["transit"].value, 50)
        self.assertEqual(late[-1].factors["transit"].value, 0)
        self.assertEqual(start.factors["incidents"].value, 100)
        self.assertLess(min(s.factors["incidents"].value for s in early), 100)
        bend = min(early, key=lambda s: s.factors["turns"].value)
        self.assertLess(bend.factors["turns"].value, 80)
        self.assertFalse(bend.factors["turns"].evidence["dark"])
        early_mean = sum(s.score for s in early) / len(early)
        late_mean = sum(s.score for s in late) / len(late)
        self.assertGreater(early_mean, late_mean)

    def test_missing_sources_stay_not_sure(self):
        bare = SegmentScorer(CFG, None, None).score_route(self.segments[:1], EIGHT_PM)[0]
        for name in ("open_places", "lighting", "activity", "incidents", "transit"):
            self.assertIsNone(bare.factors[name].value, name)
        self.assertIsNotNone(bare.factors["turns"].value)
