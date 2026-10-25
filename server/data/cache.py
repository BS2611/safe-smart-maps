"""File cache + background refresh around any PlacesProvider.

A live Bright Data fetch takes ~3 minutes and costs credit, so a route request must
never trigger one. `CachedPlacesProvider.get_places` only reads the cache. Fetches are
started by `request_refresh` (background thread) or `refresh` (blocking, for scripts).

Cache key: (provider, area). `hour_bucket` from CONTRACTS is not used: listings are not
hour-specific, callers apply evaluate_open_status(place, time) to the cached hours.
"""
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from server.data.models import BoundingBox, Place
from server.data.places import PlacesProvider

DEFAULT_CACHE_DIR = ".cache/places"
DEFAULT_TTL_SECONDS = 86400  # 24 h: a paid 3-minute fetch should not repeat every 15 min


def area_key(provider: str, area: BoundingBox) -> str:
    return f"{provider}_{area.south:.4f}_{area.west:.4f}_{area.north:.4f}_{area.east:.4f}"


def _covers(outer: BoundingBox, inner: BoundingBox) -> bool:
    return (outer.south <= inner.south and outer.west <= inner.west
            and outer.north >= inner.north and outer.east >= inner.east)


def place_to_json(p: Place) -> dict:
    return {
        "name": p.name, "lat": p.lat, "lng": p.lng, "category": p.category,
        "source": p.source, "fetched_at": p.fetched_at.isoformat(),
        "weekly_hours": None if p.weekly_hours is None else
        {str(d): [list(iv) for iv in ivs] for d, ivs in p.weekly_hours.items()},
        "is_24h": p.is_24h, "place_id": p.place_id, "raw_category": p.raw_category,
    }


def place_from_json(d: dict) -> Place:
    wh = d["weekly_hours"]
    return Place(
        name=d["name"], lat=d["lat"], lng=d["lng"], category=d["category"],
        source=d["source"], fetched_at=datetime.fromisoformat(d["fetched_at"]),
        weekly_hours=None if wh is None else
        {int(k): [(a, b) for a, b in v] for k, v in wh.items()},
        is_24h=d["is_24h"], place_id=d.get("place_id"), raw_category=d.get("raw_category"),
    )


@dataclass(frozen=True)
class CacheEntry:
    provider: str
    area: BoundingBox
    fetched_at: datetime
    places: list[Place]


@dataclass(frozen=True)
class CacheLookup:
    status: str                       # "fresh" | "stale" | "miss"
    places: list[Place]
    fetched_at: datetime | None       # data time; None on a miss
    refreshing: bool


class FilePlacesCache:
    """One JSON file per area. Writes are atomic; a corrupt file counts as a miss."""

    def __init__(self, directory: str | os.PathLike = DEFAULT_CACHE_DIR):
        self.directory = Path(directory)

    def _path(self, provider: str, area: BoundingBox) -> Path:
        return self.directory / f"{area_key(provider, area)}.json"

    def put(self, entry: CacheEntry) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        a = entry.area
        doc = {"provider": entry.provider,
               "area": {"south": a.south, "west": a.west, "north": a.north, "east": a.east},
               "fetched_at": entry.fetched_at.isoformat(),
               "places": [place_to_json(p) for p in entry.places]}
        fd, tmp = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(doc, f)
            os.replace(tmp, self._path(entry.provider, a))
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    @staticmethod
    def _read(path: Path) -> CacheEntry | None:
        try:
            doc = json.loads(path.read_text())
            return CacheEntry(
                provider=doc["provider"], area=BoundingBox(**doc["area"]),
                fetched_at=datetime.fromisoformat(doc["fetched_at"]),
                places=[place_from_json(p) for p in doc["places"]])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def entries(self, provider: str | None = None) -> list[CacheEntry]:
        if not self.directory.is_dir():
            return []
        found = (self._read(p) for p in sorted(self.directory.glob("*.json")))
        return [e for e in found if e and (provider is None or e.provider == provider)]

    def find(self, provider: str, area: BoundingBox) -> CacheEntry | None:
        """Exact entry for `area`, else the newest entry whose area covers it."""
        exact = self._read(self._path(provider, area))
        if exact:
            return exact
        covering = [e for e in self.entries(provider) if _covers(e.area, area)]
        return max(covering, key=lambda e: e.fetched_at, default=None)


class CachedPlacesProvider(PlacesProvider):
    def __init__(self, upstream: PlacesProvider, cache: FilePlacesCache, provider_name: str,
                 ttl_seconds: float = DEFAULT_TTL_SECONDS):
        self.upstream = upstream
        self.cache = cache
        self.provider_name = provider_name
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._in_flight: set[str] = set()
        self.last_error: dict[str, str] = {}     # area key -> error class + message, no secrets

    def _is_fresh(self, fetched_at: datetime, now: datetime) -> bool:
        return (now - fetched_at).total_seconds() <= self.ttl_seconds

    def is_refreshing(self, area: BoundingBox) -> bool:
        with self._lock:
            return area_key(self.provider_name, area) in self._in_flight

    def lookup(self, area: BoundingBox, now: datetime | None = None) -> CacheLookup:
        """Cache read only. Never touches the network."""
        now = now or datetime.now(timezone.utc)
        refreshing = self.is_refreshing(area)
        entry = self.cache.find(self.provider_name, area)
        if entry is None:
            return CacheLookup("miss", [], None, refreshing)
        status = "fresh" if self._is_fresh(entry.fetched_at, now) else "stale"
        inside = [p for p in entry.places if area.contains(p.lat, p.lng)]
        return CacheLookup(status, inside, entry.fetched_at, refreshing)

    def get_places(self, area: BoundingBox, time: datetime) -> list[Place]:
        """Cached places only (empty on a miss, i.e. "not sure"). Never fetches."""
        return self.lookup(area).places

    def refresh(self, area: BoundingBox, time: datetime | None = None) -> int:
        """Blocking live fetch, then write the cache. Returns the number of places stored.

        On failure the old entry stays. An empty result never replaces a non-empty entry.
        """
        key = area_key(self.provider_name, area)
        with self._lock:
            if key in self._in_flight:
                return 0
            self._in_flight.add(key)
        try:
            places = self.upstream.get_places(area, time or datetime.now(timezone.utc))
            self.last_error.pop(key, None)
            old = self.cache.find(self.provider_name, area)
            if not places and old and old.places:
                self.last_error[key] = "upstream returned 0 places; kept the older entry"
                return 0
            self.cache.put(CacheEntry(self.provider_name, area, datetime.now(timezone.utc), places))
            return len(places)
        except Exception as e:
            self.last_error[key] = f"{type(e).__name__}: {e}"
            raise
        finally:
            with self._lock:
                self._in_flight.discard(key)

    def request_refresh(self, area: BoundingBox) -> bool:
        """Start a background refresh. False if one is already running for this area."""
        if self.is_refreshing(area):
            return False

        def run():
            try:
                self.refresh(area)
            except Exception:
                pass  # recorded in last_error

        threading.Thread(target=run, daemon=True, name="places-refresh").start()
        return True
