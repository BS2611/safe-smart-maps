"""Demo-area prefetch and cache status. Builds the cached places provider.

Prefetch only ever starts a BACKGROUND refresh, and only when the entry is missing or
stale. Route requests never wait on it.
"""
import os
from datetime import datetime, timezone

from server.data.apify import ApifyPlacesProvider, FallbackPlacesProvider
from server.data.brightdata import BrightDataPlacesProvider
from server.data.cache import (DEFAULT_CACHE_DIR, DEFAULT_TTL_SECONDS, CachedPlacesProvider,
                               FilePlacesCache, area_key)
from server.data.models import BoundingBox

PROVIDER_NAME = "brightdata"

# Areas to keep warm for the demo (configuration, not business data).
DEMO_AREAS: dict[str, BoundingBox] = {
    "palace_of_fine_arts": BoundingBox(south=37.797, west=-122.455, north=37.809, east=-122.440),
}


def build_places_provider() -> CachedPlacesProvider:
    ttl = float(os.environ.get("CACHE_TTL_SECONDS") or DEFAULT_TTL_SECONDS)
    cache = FilePlacesCache(os.environ.get("CACHE_DIR") or DEFAULT_CACHE_DIR)
    # Apify only runs when Bright Data fails (and APIFY_TOKEN is set); Place.source says which one answered.
    upstream = FallbackPlacesProvider(BrightDataPlacesProvider(), ApifyPlacesProvider(),
                                      ApifyPlacesProvider.configured)
    return CachedPlacesProvider(upstream, cache, PROVIDER_NAME, ttl)


def prefetch_enabled() -> bool:
    return os.environ.get("PREFETCH_ON_STARTUP", "1") != "0" and bool(os.environ.get("BRIGHTDATA_API_KEY"))


def start_prefetch(provider: CachedPlacesProvider, areas: dict[str, BoundingBox] = DEMO_AREAS) -> list[str]:
    """Start background refreshes for areas that are missing or stale. Returns their names."""
    started = []
    for name, area in areas.items():
        if provider.lookup(area).status != "fresh" and provider.request_refresh(area):
            started.append(name)
    return started


def cache_status(provider: CachedPlacesProvider, areas: dict[str, BoundingBox] = DEMO_AREAS) -> dict:
    now = datetime.now(timezone.utc)
    out = []
    for name, area in areas.items():
        look = provider.lookup(area, now)
        err = provider.last_error.get(area_key(provider.provider_name, area))
        out.append({
            "area": name,
            "status": look.status,            # fresh | stale | miss
            "refreshing": look.refreshing,
            "places": len(look.places),
            "data_fetched_at": look.fetched_at.isoformat() if look.fetched_at else None,
            "age_seconds": int((now - look.fetched_at).total_seconds()) if look.fetched_at else None,
            "last_error": err,
        })
    return {"api_version": "1", "provider": provider.provider_name,
            "ttl_seconds": provider.ttl_seconds, "areas": out}

