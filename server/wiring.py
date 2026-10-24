"""Builds the real planner from environment settings. Kept apart so tests can build their own."""
import os

from server.data.brightdata import BrightDataPlacesProvider
from server.data.cache import TTLCache
from server.data.mapbox import MapboxRoutingProvider
from server.data.osm import OverpassProvider
from server.data.sf_open_data import SocrataClient
from server.data.transit import NoTransitProvider
from server.services.explain import ClaudeExplainer
from server.services.planner import Providers, RoutePlanner


def build_planner(cfg: dict) -> RoutePlanner:
    ttl = float(os.environ.get("CACHE_TTL_SECONDS", "900"))
    providers = Providers(
        routing=MapboxRoutingProvider(),
        places=BrightDataPlacesProvider(),
        osm=OverpassProvider(),
        sf=SocrataClient(),
        transit=NoTransitProvider(),
        explainer=ClaudeExplainer(),
    )
    return RoutePlanner(providers, cfg, cache=TTLCache(ttl))
