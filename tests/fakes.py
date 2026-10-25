"""LABELED TEST FIXTURES: fake providers and a small invented scenario (see AGENTS.md section 6).

Nothing here is real data and none of it is used outside tests. The scenario is a short trip near
the Palace of Fine Arts. Route B is a longer, lit main road with restaurants that close by
11:30 PM. Route A is the direct residential street with a few night-owl places open until 3 AM.
At 8 PM route B is better lit and more active; by 1 AM its restaurants have closed.

Points handed to routing are (lng, lat); everything else in the backend uses (lat, lng).
"""
from datetime import datetime, timezone
from pathlib import Path

from server.data.cache import CachedPlacesProvider, CacheEntry, FilePlacesCache
from server.data.mapbox import MapboxError, RouteCandidate
from server.data.models import AreaContext, BoundingBox, HelpPoint, Place, RoadContext
from server.data.osm import OsmError
from server.data.places import PlacesProvider
from server.services.explain import template_explanation
from server.services.planner import Providers, RoutePlanner
from server.services.scoring_config import load_scoring_config

ORIGIN = (-122.4484, 37.8029)   # (lng, lat)
DEST = (-122.4400, 37.8029)
FETCHED = datetime(2026, 10, 24, 22, 31, tzinfo=timezone.utc)
CACHE_AREA = BoundingBox(37.80, -122.45, 37.81, -122.43)   # covers both routes

ROUTE_A_LNGLAT = [ORIGIN, (-122.4442, 37.8029), DEST]
ROUTE_B_LNGLAT = [ORIGIN, (-122.4470, 37.8060), (-122.4415, 37.8060), DEST]

# Hours as (open_minute, close_minute) from local midnight.
EVENING = {d: [(1080, 1410)] for d in range(7)}   # 6 PM to 11:30 PM (closed by 1 AM)
NIGHT_OWL = {d: [(1020, 1620)] for d in range(7)}  # 5 PM to 3 AM (still open at 1 AM)
DAYTIME = {d: [(480, 1260)] for d in range(7)}     # 8 AM to 9 PM


def route_a(route_id="mapbox-0") -> RouteCandidate:
    return RouteCandidate(route_id, "mapbox", list(ROUTE_A_LNGLAT), 740.0, 540.0)


def route_b(route_id="mapbox-1") -> RouteCandidate:
    return RouteCandidate(route_id, "mapbox", list(ROUTE_B_LNGLAT), 1050.0, 780.0)


def place(name, lng, lat, category, hours, is_24h=None) -> Place:
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


def area_context(fetched_at: datetime = FETCHED) -> AreaContext:
    road_a = RoadContext(tuple((lat, lng) for lng, lat in ROUTE_A_LNGLAT), "residential", "unknown",
                         "osm", fetched_at, osm_id=1, name="Marina Blvd")
    road_b = RoadContext(tuple((lat, lng) for lng, lat in ROUTE_B_LNGLAT), "primary", "yes",
                         "osm", fetched_at, osm_id=2, name="Lombard St")
    police = HelpPoint("police", 37.8062, -122.4470, "osm", fetched_at, name="Fixture Police Station",
                       osm_id=3)
    return AreaContext([road_a, road_b], [police], fetched_at)


class FakeRouting:
    """Mapbox stand-in. Detours (calls with waypoints) fail with `empty` unless given routes."""

    def __init__(self, candidates=None, error=None, detours=None):
        self.candidates = [route_a(), route_b()] if candidates is None else candidates
        self.error = error
        self.detours = detours
        self.calls: list[tuple] = []

    def get_walking_routes(self, origin, dest, waypoints=()):
        self.calls.append((origin, dest, tuple(waypoints)))
        if self.error:
            raise self.error
        if waypoints:
            if self.detours is None:
                raise MapboxError("no walking route found between these points", kind="empty")
            return self.detours
        return self.candidates


class FakeContext:
    def __init__(self, error=None, context=None):
        self.error = error
        self.context = context or area_context()
        self.calls = 0

    def get_area_context(self, area):
        self.calls += 1
        if self.error:
            raise self.error
        return self.context


class FakeUpstream(PlacesProvider):
    def get_places(self, area, time):  # never used: route requests only read the cache
        raise AssertionError("a route request must not fetch places")


class FakeExplainer:
    """Records the facts it was given. Default text is the real template wording."""

    def __init__(self, text=None, source="template"):
        self.text, self.source = text, source
        self.seen = []

    def explain(self, facts):
        self.seen.append(facts)
        return (self.text or template_explanation(facts)), self.source


def make_places_provider(directory: Path, stored: list[Place] | None = None,
                         area: BoundingBox = CACHE_AREA, fetched_at: datetime | None = None,
                         ttl_seconds: float = 10 ** 9) -> CachedPlacesProvider:
    """The real cache class on a temp folder. `stored=None` leaves the cache empty (a miss)."""
    cache = FilePlacesCache(directory)
    if stored is not None:
        cache.put(CacheEntry("brightdata", area, fetched_at or FETCHED, stored))
    return CachedPlacesProvider(FakeUpstream(), cache, "brightdata", ttl_seconds)


def make_planner(directory: Path, **overrides) -> RoutePlanner:
    providers = Providers(
        routing=overrides.get("routing", FakeRouting()),
        places=overrides["places"] if "places" in overrides else make_places_provider(directory, places()),
        context=overrides.get("context", FakeContext()),
        explainer=overrides.get("explainer", FakeExplainer()),
        sf=overrides.get("sf"),  # None = SF open data not connected, so those factors stay not sure
    )
    return RoutePlanner(providers, load_scoring_config())


class FakeSf:
    """LABELED FIXTURE for SF open data: fixed incident and streetlight-outage lists, or an error."""

    def __init__(self, incidents=(), outages=(), error=None):
        self.incidents, self.outages, self.error = list(incidents), list(outages), error
        self.calls = 0

    def get_recent_incidents(self, area):
        self.calls += 1
        if self.error:
            raise self.error
        return self.incidents

    def get_open_outages(self, area):
        self.calls += 1
        if self.error:
            raise self.error
        return self.outages


def osm_down() -> OsmError:
    return OsmError("Overpass returned HTTP 502")
