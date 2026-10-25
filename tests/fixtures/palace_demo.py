"""TEST/DEMO FIXTURE ONLY. Hand-written coordinates and context around the Palace of Fine Arts.

None of this is real business, road or help-point data. It exists to exercise the
segmenter + scorer before the Mapbox route provider exists. Never import it from server/.
"""
from datetime import datetime, timezone

from server.data.models import AreaContext, HelpPoint, Place, RoadContext

FETCHED = datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc)

# ~330 m south, then ~150 m east (lat, lng)
ROUTE = [(37.8050, -122.4484), (37.8035, -122.4484), (37.8020, -122.4484), (37.8020, -122.4467)]

WEEK_EVENING = {d: [(17 * 60, 23 * 60)] for d in range(7)}      # 5 PM - 11 PM every day


def place(name, lat, lng, hours=WEEK_EVENING):
    return Place(name=name, lat=lat, lng=lng, category="cafe", source="test-fixture",
                 fetched_at=FETCHED, weekly_hours=hours, is_24h=None)


PLACES = [
    place("TEST open evening cafe A", 37.8036, -122.4485),
    place("TEST open evening cafe B", 37.8037, -122.4483),
    place("TEST morning-only bakery", 37.8021, -122.4480, {d: [(6 * 60, 12 * 60)] for d in range(7)}),
    place("TEST unknown-hours shop", 37.8022, -122.4470, None),
]

ROADS = [
    RoadContext(coordinates=((37.8055, -122.4484), (37.8020, -122.4484)), road_class="primary",
                lit="yes", source="test-fixture", fetched_at=FETCHED, name="TEST Main St"),
    RoadContext(coordinates=((37.8020, -122.4484), (37.8020, -122.4460)), road_class="residential",
                lit="unknown", source="test-fixture", fetched_at=FETCHED, name="TEST Side St"),
]

HELP_POINTS = [HelpPoint(type="police", lat=37.8040, lng=-122.4490, source="test-fixture",
                         fetched_at=FETCHED, name="TEST police station")]

AREA = AreaContext(roads=ROADS, help_points=HELP_POINTS, fetched_at=FETCHED)
