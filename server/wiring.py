"""Builds the real planner from environment settings. Kept apart so tests can build their own."""
import os
from pathlib import Path

from server.data.cache import CachedPlacesProvider
from server.data.gtfs import TransitFeedError, load_gtfs
from server.data.mapbox import MapboxWalkingProvider
from server.data.osm import OverpassContextProvider
from server.data.sf_open_data import SocrataClient
from server.services.explain import ClaudeExplainer
from server.services.planner import Providers, RoutePlanner


def _transit_schedule():
    raw = os.environ.get("GTFS_DIR", "").strip()
    if not raw:
        return None
    try:
        return load_gtfs(Path(raw))
    except TransitFeedError:
        return None


def build_planner(cfg: dict, places: CachedPlacesProvider) -> RoutePlanner:
    """`places` is the same cached provider the /v1/cache/status route and the prefetch use."""
    city = SocrataClient()
    providers = Providers(
        routing=MapboxWalkingProvider(),     # reads MAPBOX_TOKEN when a request is made
        places=places,
        context=OverpassContextProvider(),
        explainer=ClaudeExplainer(),         # reads ANTHROPIC_API_KEY; template text without it
        incidents=city,
        outages=city,
        transit=_transit_schedule(),         # GTFS_DIR; empty means transit stays not sure
    )
    return RoutePlanner(providers, cfg)
