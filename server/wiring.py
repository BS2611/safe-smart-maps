"""Builds the real planner from environment settings. Kept apart so tests can build their own."""
import os
from pathlib import Path

from server.data.brightdata import BrightDataPlacesProvider
from server.data.cache import TTLCache
from server.data.mapbox import MapboxRoutingProvider
from server.data.osm import OverpassProvider
from server.data.places_cache import CachedPlacesProvider
from server.data.sf_open_data import SocrataClient
from server.data.transit import NoTransitProvider
from server.services.explain import ClaudeExplainer
from server.services.planner import Providers, RoutePlanner


def build_planner(cfg: dict) -> RoutePlanner:
    ttl = float(os.environ.get("CACHE_TTL_SECONDS", "900"))
    providers = Providers(
        routing=MapboxRoutingProvider(),
        # Live listings take 60-100 s per area, so each area is also saved to disk (default 24 h).
        places=CachedPlacesProvider(
            BrightDataPlacesProvider(),
            Path(os.environ.get("PLACES_CACHE_DIR") or ".cache/places"),
            ttl_s=float(os.environ.get("PLACES_CACHE_HOURS") or 24) * 3600,
        ),
        osm=OverpassProvider(cache_dir=Path(os.environ.get("MAP_CACHE_DIR") or ".cache/osm")),
        sf=SocrataClient(),
        transit=NoTransitProvider(),
        explainer=ClaudeExplainer(),
    )
    budgets = {}
    if os.environ.get("PLACES_BUDGET_SECONDS"):
        budgets["places"] = float(os.environ["PLACES_BUDGET_SECONDS"])
    if os.environ.get("SOURCE_BUDGET_SECONDS"):
        budgets["default"] = float(os.environ["SOURCE_BUDGET_SECONDS"])
    return RoutePlanner(providers, cfg, cache=TTLCache(ttl), budgets=budgets)
