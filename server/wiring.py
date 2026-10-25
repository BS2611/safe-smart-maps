"""Builds the real planner from environment settings. Kept apart so tests can build their own."""
import os
from pathlib import Path

from server.data.cache import CachedPlacesProvider
from server.data.gtfs import CombinedSchedule, TransitFeedError, TransitUnavailable, load_gtfs
from server.data.mapbox import MapboxWalkingProvider
from server.data.mapillary import MapillaryPhotoSource
from server.data.osm import OverpassContextProvider
from server.data.sf_open_data import SocrataClient
from server.services.audit import StreetAuditor
from server.services.explain import build_explainer
from server.services.planner import Providers, RoutePlanner


def _transit_schedule():
    """None when no feed is configured. A bad path is also None so the factor stays not sure."""
    paths = [item for item in (
        os.environ.get("GTFS_DIR", "").strip(),
        os.environ.get("GTFS_DIR_EXTRA", "").strip(),
    ) if item]
    if not paths:
        return None
    loaded = []
    failed = False
    for raw in paths:
        try:
            loaded.append(load_gtfs(Path(raw)))
        except TransitFeedError:
            failed = True
    if not loaded:
        return TransitUnavailable()
    schedule = loaded[0] if len(loaded) == 1 else CombinedSchedule(loaded)
    schedule.partial_failure = failed
    return schedule


def build_planner(cfg: dict, places: CachedPlacesProvider) -> RoutePlanner:
    """`places` is the same cached provider the /v1/cache/status route and the prefetch use."""
    city = SocrataClient()
    providers = Providers(
        routing=MapboxWalkingProvider(),     # reads MAPBOX_TOKEN when a request is made
        places=places,
        context=OverpassContextProvider(),
        explainer=build_explainer(),         # Claude by default (ANTHROPIC_API_KEY); template text without a key
        incidents=city,
        outages=city,
        transit=_transit_schedule(),         # GTFS_DIR; empty means transit stays not sure
        auditor=StreetAuditor(),             # reads ANTHROPIC_API_KEY; no key = no audits
        photos=MapillaryPhotoSource(),       # reads MAPILLARY_TOKEN; no token = no photos
    )
    return RoutePlanner(providers, cfg)
