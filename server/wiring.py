"""Builds the real planner from environment settings. Kept apart so tests can build their own."""
from server.data.cache import CachedPlacesProvider
from server.data.mapbox import MapboxWalkingProvider
from server.data.osm import OverpassContextProvider
from server.services.explain import ClaudeExplainer
from server.services.planner import Providers, RoutePlanner


def build_planner(cfg: dict, places: CachedPlacesProvider) -> RoutePlanner:
    """`places` is the same cached provider the /v1/cache/status route and the prefetch use."""
    providers = Providers(
        routing=MapboxWalkingProvider(),     # reads MAPBOX_TOKEN when a request is made
        places=places,
        context=OverpassContextProvider(),
        explainer=ClaudeExplainer(),         # reads ANTHROPIC_API_KEY; template text without it
    )
    return RoutePlanner(providers, cfg)
