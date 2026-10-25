"""Builds the real planner from environment settings. Kept apart so tests can build their own."""
from server.data.cache import CachedPlacesProvider
from server.data.mapbox import MapboxWalkingProvider
from server.data.osm import OverpassContextProvider
from server.data.sf_open_data import SocrataClient
from server.data.transit import Muni511Provider
from server.services.explain import build_explainer
from server.services.planner import Providers, RoutePlanner


def build_planner(cfg: dict, places: CachedPlacesProvider) -> RoutePlanner:
    """`places` is the same cached provider the /v1/cache/status route and the prefetch use."""
    providers = Providers(
        routing=MapboxWalkingProvider(),     # reads MAPBOX_TOKEN when a request is made
        places=places,
        context=OverpassContextProvider(),
        explainer=build_explainer(),          # Claude by default (ANTHROPIC_API_KEY); template text without a key
        transit=Muni511Provider(),           # reads API_511_KEY; transit shows not sure without it
        sf=SocrataClient(),                  # public SF open data, no key: incidents + streetlight reports
    )
    return RoutePlanner(providers, cfg)
