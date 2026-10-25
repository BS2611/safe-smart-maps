"""Reads saved business listings for a route's area from the places cache (server/data/cache.py).

A route request must never start a paid, minutes-long Bright Data fetch, so this only READS the
cache. No saved listing near the route -> `places=None` ("not sure"), never an empty list.
"""
from dataclasses import dataclass
from datetime import datetime

from server.data.cache import CachedPlacesProvider
from server.data.models import BoundingBox, Place


@dataclass(frozen=True)
class PlacesResult:
    places: list[Place] | None      # None = no listings available for this area
    fetched_at: datetime | None     # oldest listing time used
    warning: str | None


def _overlaps(a: BoundingBox, b: BoundingBox) -> bool:
    return a.south <= b.north and b.south <= a.north and a.west <= b.east and b.west <= a.east


def _key(p: Place) -> str:
    return p.place_id or f"{p.name}|{p.lat}|{p.lng}"


def places_for_area(provider: CachedPlacesProvider, area: BoundingBox) -> PlacesResult:
    look = provider.lookup(area)
    if look.status != "miss":
        warning = None
        if look.status == "stale":
            warning = (f"Business listings are older than {provider.ttl_seconds / 3600:g} hours "
                       f"(saved {look.fetched_at:%b %d %H:%M} UTC); they may have changed.")
        return PlacesResult(look.places, look.fetched_at, warning)

    parts = [e for e in provider.cache.entries(provider.provider_name) if _overlaps(e.area, area)]
    if not parts:
        return PlacesResult(None, None, "Business listings are not saved for this area yet, "
                                        "so open places show as not sure.")
    merged: dict[str, Place] = {}
    for entry in parts:
        for p in entry.places:
            if area.contains(p.lat, p.lng):
                merged[_key(p)] = p
    return PlacesResult(
        list(merged.values()), min(e.fetched_at for e in parts),
        "Business listings are saved for only part of this route's area; places outside it "
        "are not counted.")
