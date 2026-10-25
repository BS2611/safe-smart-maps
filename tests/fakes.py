"""LABELED TEST FIXTURES: fake providers and a small invented scenario (see AGENTS.md section 6).

Nothing here is real data and none of it is used outside tests. The scenario is a short trip
near the Palace of Fine Arts. Route B is a longer, lit main road with restaurants that close by 11:30 PM. Route A is the
direct street with a few night-owl places open until 3 AM. At 8 PM route B is better lit and
more active; by 1 AM its restaurants have closed and route A is recommended.
"""
from datetime import datetime, timezone

from server.data.errors import DataSourceError, NotConfiguredError
from server.data.mapbox import RouteCandidate, Step, make_route_id
from server.data.models import BoundingBox, Place
from server.data.osm import HelpPoint, MapFeatures, Way
from server.data.sf_open_data import Incident, Outage
from server.data.transit import NoTransitProvider
from server.services.explain import template_explanation
from server.services.planner import Providers, RoutePlanner
from server.services.scoring_config import load_scoring_config

ORIGIN = (-122.4484, 37.8029)
DEST = (-122.4400, 37.8029)
FETCHED = datetime(2026, 10, 24, 22, 31, tzinfo=timezone.utc)

ROUTE_A_COORDS = [ORIGIN, (-122.4442, 37.8029), DEST]
ROUTE_B_COORDS = [ORIGIN, (-122.4470, 37.8060), (-122.4415, 37.8060), DEST]

# Hours as (open_minute, close_minute) from local midnight.
EVENING = {d: [(1080, 1410)] for d in range(7)}   # 6 PM to 11:30 PM (closed by 1 AM)
NIGHT_OWL = {d: [(1020, 1620)] for d in range(7)}  # 5 PM to 3 AM (still open at 1 AM)
DAYTIME = {d: [(480, 1260)] for d in range(7)}     # 8 AM to 9 PM


def route_a() -> RouteCandidate:
    return RouteCandidate(make_route_id(ROUTE_A_COORDS), ROUTE_A_COORDS, 740.0, 540.0,
                          [Step("Lyon St", 300.0), Step("Marina Blvd", 440.0)])


def route_b() -> RouteCandidate:
    return RouteCandidate(make_route_id(ROUTE_B_COORDS), ROUTE_B_COORDS, 1050.0, 780.0,
                          [Step("Lombard St", 700.0), Step("Fillmore St", 350.0)])


def place(name, lng, lat, category, hours, is_24h=None):
    return Place(name, lat, lng, category, "fixture", FETCHED, hours, is_24h, place_id=f"fx-{name}")


def places() -> list[Place]:
    evening = [place(f"Evening Diner {i}", -122.4476 + i * 0.0008, 37.80605, "restaurant", EVENING)
               for i in range(9)]
    night_owls = [place(f"Night Owl {i}", -122.4474 + i * 0.0012, 37.80295, "restaurant", NIGHT_OWL)
                  for i in range(3)]
    return evening + night_owls + [
        place("Day Cafe", -122.4442, 37.80295, "cafe", DAYTIME),
        place("All Night Pharmacy", -122.4430, 37.80605, "pharmacy", None, is_24h=True),
        place("Mystery Shop", -122.4450, 37.80295, "other", None),  # hours unreadable
    ]


def features() -> MapFeatures:
    ways = [
        Way(1, "residential", None, False, "Marina Blvd", ROUTE_A_COORDS),
        Way(2, "primary", True, False, "Lombard St", ROUTE_B_COORDS),
    ]
    helps = [HelpPoint("Fixture Police Station", "police", -122.4470, 37.8062, "fixture")]
    return MapFeatures(ways, helps, FETCHED)


class FakeRouting:
    def __init__(self, candidates=None, error=None):
        self.candidates = [route_a(), route_b()] if candidates is None else candidates
        self.error = error
        self.calls = 0

    def get_walking_routes(self, origin, dest):
        self.calls += 1
        if self.error:
            raise self.error
        return self.candidates


class FakePlaces:
    def __init__(self, error=None, partial_fail_cells=0):
        self.error = error
        self.calls = 0
        self.partial_fail_cells = partial_fail_cells

    def get_places(self, area: BoundingBox, time):
        self.calls += 1
        if self.error:
            raise self.error
        if self.partial_fail_cells and self.calls <= self.partial_fail_cells:
            raise DataSourceError("brightdata", "HTTP 500")
        return [p for p in places() if area.contains(p.lat, p.lng)]


class FakeOsm:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def get_map_features(self, area):
        self.calls += 1
        if self.error:
            raise self.error
        return features()


class FakeSf:
    def __init__(self, outages=None, incidents=None, error=None):
        self.outages = [] if outages is None else outages
        self.incidents = [] if incidents is None else incidents
        self.error = error

    def get_open_outages(self, area):
        if self.error:
            raise self.error
        return self.outages

    def get_recent_incidents(self, area):
        if self.error:
            raise self.error
        return self.incidents


class FakeExplainer:
    """Records the facts it was given. Default text is the real template wording."""

    def __init__(self, text=None, source="template"):
        self.text, self.source = text, source
        self.seen = []

    def explain(self, facts):
        self.seen.append(facts)
        return (self.text or template_explanation(facts)), self.source


def make_planner(**overrides) -> RoutePlanner:
    providers = Providers(
        routing=overrides.get("routing", FakeRouting()),
        places=overrides.get("places", FakePlaces()),
        osm=overrides.get("osm", FakeOsm()),
        sf=overrides.get("sf", FakeSf()),
        transit=overrides.get("transit", NoTransitProvider()),
        explainer=overrides.get("explainer", FakeExplainer()),
    )
    return RoutePlanner(providers, load_scoring_config())


def not_configured(source="mapbox", what="MAPBOX_TOKEN"):
    return NotConfiguredError(source, what)


__all__ = ["ORIGIN", "DEST", "Incident", "Outage"]
