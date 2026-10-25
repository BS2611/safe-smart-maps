"""Each scoring factor, with labeled fixtures only. No network."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from server.data.gtfs import TransitSchedule, _Freq, _Service, _Stop, _Visit
from server.data.models import ActivityPoint, StreetLamp
from server.data.sf_open_data import Incident, Outage
from server.services.scoring_config import load_scoring_config
from server.services.segment_scoring import SegmentScorer
from server.services.segmenter import segment_route
from tests.test_segment_scoring import EVENING, FETCHED, area, north, place, road

PT = ZoneInfo("America/Los_Angeles")
ONE_AM = datetime(2026, 10, 25, 1, 0, tzinfo=PT)
CFG = load_scoring_config()
M = 1 / 111_195


def bend():
    start = north(0)
    corner = north(20)
    end = (corner[0], corner[1] + 20 * M * 1.26)
    return segment_route([start, corner, end], 50)[0]


class LightingTests(unittest.TestCase):
    def score(self, lit="unknown", lamps=(), outages=None):
        ctx = area([road(lit=lit)])
        ctx = type(ctx)(ctx.roads, ctx.help_points, ctx.fetched_at, list(lamps), [], False)
        return SegmentScorer(CFG, [], ctx, outages=outages).score_segment(
            segment_route([(37.8, -122.45), (37.8 + 50 * M, -122.45)])[0], EVENING).factors["lighting"]

    def test_unknown_tag_is_not_unlit(self):
        missing = self.score("unknown")
        unlit = self.score("no")
        self.assertIsNone(missing.value)
        self.assertEqual(unlit.value, 0)

    def test_nearby_lamp_scores_without_calling_the_street_unlit(self):
        lamp = StreetLamp(*north(25))
        lit = self.score("unknown", lamps=[lamp])
        self.assertGreater(lit.value, 0)
        self.assertIn("not sure", lit.reason)

    def test_open_outage_lowers_a_lit_street(self):
        plain = self.score("yes")
        outage = self.score("yes", outages=[Outage(-122.45, north(25)[0], "2026-10-24")])
        self.assertEqual(plain.value, 100)
        self.assertLess(outage.value, plain.value)
        self.assertGreater(outage.value, 0)


class TurnTests(unittest.TestCase):
    def test_straight_is_high_and_a_corner_is_lower(self):
        straight = SegmentScorer(CFG, [], area([road()])).score_segment(
            segment_route([(37.8, -122.45), (37.8 + 50 * M, -122.45)])[0], EVENING)
        corner = SegmentScorer(CFG, [], area([road()])).score_segment(bend(), EVENING)
        self.assertEqual(straight.factors["turns"].value, 100)
        self.assertLess(corner.factors["turns"].value, 80)

    def test_dark_penalty_needs_an_unlit_tag(self):
        unlit = SegmentScorer(CFG, [], area([road(lit="no")])).score_segment(bend(), EVENING)
        unknown = SegmentScorer(CFG, [], area([road(lit="unknown")])).score_segment(bend(), EVENING)
        self.assertLess(unlit.factors["turns"].value, unknown.factors["turns"].value)
        self.assertTrue(unlit.factors["turns"].evidence["dark"])
        self.assertFalse(unknown.factors["turns"].evidence["dark"])

    def test_tunnel_tag_lowers_the_turn_score(self):
        tagged = road()
        under = type(tagged)(tagged.coordinates, tagged.road_class, tagged.lit, tagged.source,
                             tagged.fetched_at, tunnel=True)
        plain = SegmentScorer(CFG, [], area([road()])).score_segment(bend(), EVENING)
        buried = SegmentScorer(CFG, [], area([under])).score_segment(bend(), EVENING)
        self.assertLess(buried.factors["turns"].value, plain.factors["turns"].value)
        self.assertIn("underpass", buried.factors["turns"].reason)


class ActivityIncidentTransitTests(unittest.TestCase):
    def segment(self):
        return segment_route([(37.8, -122.45), (37.8 + 50 * M, -122.45)])[0]

    def test_activity_uses_place_density_and_the_hour(self):
        ctx = area([road()])
        ctx = type(ctx)(ctx.roads, ctx.help_points, FETCHED, [], [ActivityPoint(*north(25), "cafe")], True)
        scorer = SegmentScorer(CFG, [], ctx)
        evening = scorer.score_segment(self.segment(), EVENING).factors["activity"]
        late = scorer.score_segment(self.segment(), ONE_AM).factors["activity"]
        self.assertGreater(evening.value, late.value)
        self.assertIn("estimate", evening.reason)
        missing = SegmentScorer(CFG, [], area()).score_segment(self.segment(), EVENING)
        self.assertIsNone(missing.factors["activity"].value)

    def test_incidents_stay_unknown_without_data_and_drop_as_reports_increase(self):
        seg = self.segment()
        none = SegmentScorer(CFG, [], area(), incidents=None).score_segment(seg, EVENING)
        clear = SegmentScorer(CFG, [], area(), incidents=[]).score_segment(seg, EVENING)
        near = Incident(north(25)[1], north(25)[0], "test")
        hit = SegmentScorer(CFG, [], area(), incidents=[near, near, near]).score_segment(seg, EVENING)
        self.assertIsNone(none.factors["incidents"].value)
        self.assertEqual(clear.factors["incidents"].value, 100)
        self.assertLess(hit.factors["incidents"].value, 50)
        self.assertNotIn("danger", hit.factors["incidents"].reason)

    def test_transit_needs_a_departure_in_the_window(self):
        stop = _Stop("s", "Test stop", *north(10))
        visit = _Visit("s", "wk", 20 * 60 + 10)
        service = _Service(days=(True,) * 7, start="20260101", end="20261231")
        schedule = TransitSchedule({"s": stop}, [visit], {"wk": service}, [])
        seg = self.segment()
        with_feed = SegmentScorer(CFG, [], area(), transit=schedule)
        evening = with_feed.score_segment(seg, EVENING).factors["transit"]
        late = with_feed.score_segment(seg, ONE_AM).factors["transit"]
        self.assertGreater(evening.value, 50)
        self.assertEqual(late.value, 0)
        self.assertIsNone(SegmentScorer(CFG, [], area()).score_segment(seg, EVENING).factors["transit"].value)

    def test_frequency_window_counts_as_service(self):
        stop = _Stop("s", "Bus", *north(10))
        service = _Service(days=(True,) * 7, start="20260101", end="20261231")
        freq = _Freq("wk", ("s",), 18 * 60, 23 * 60)
        schedule = TransitSchedule({"s": stop}, [], {"wk": service}, [freq])
        seg = self.segment()
        scorer = SegmentScorer(CFG, [], area(), transit=schedule)
        self.assertGreater(scorer.score_segment(seg, EVENING).factors["transit"].value, 50)
        self.assertEqual(scorer.score_segment(seg, ONE_AM).factors["transit"].value, 0)

    def test_open_place_hours_follow_arrival(self):
        scorer = SegmentScorer(CFG, [place()], area())
        seg = self.segment()
        self.assertEqual(scorer.score_segment(seg, EVENING).factors["open_places"].value, 50)
        self.assertEqual(scorer.score_segment(seg, ONE_AM).factors["open_places"].value, 0)
