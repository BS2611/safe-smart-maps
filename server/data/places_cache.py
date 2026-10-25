"""Saves live business listings to disk, per area, so a restart or a slow/failed fetch does not mean
waiting minutes (a Bright Data lookup takes 60-100 s per area) or paying for the same lookup twice.

Fresh copy (younger than `ttl_s`): used without calling Bright Data. Stale copy: only used if the live
fetch fails, and its real fetched time is kept, so the app shows how old the data is.
"""
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from server.data.models import BoundingBox, Place
from server.data.places import PlacesProvider

log = logging.getLogger("places_cache")


def place_to_json(p: Place) -> dict[str, Any]:
    d = asdict(p)
    d["fetched_at"] = p.fetched_at.isoformat()
    d["weekly_hours"] = (
        None if p.weekly_hours is None
        else {str(day): [list(iv) for iv in ivs] for day, ivs in p.weekly_hours.items()}
    )
    return d


def place_from_json(d: dict[str, Any]) -> Place:
    hours = d.get("weekly_hours")
    return Place(
        name=d["name"], lat=d["lat"], lng=d["lng"], category=d["category"], source=d["source"],
        fetched_at=datetime.fromisoformat(d["fetched_at"]),
        weekly_hours=None if hours is None else {int(k): [tuple(iv) for iv in v] for k, v in hours.items()},
        is_24h=d.get("is_24h"), place_id=d.get("place_id"), raw_category=d.get("raw_category"),
    )


class CachedPlacesProvider(PlacesProvider):
    def __init__(self, inner: PlacesProvider, cache_dir: Path | None, ttl_s: float = 24 * 3600,
                 clock: Callable[[], float] = time.time):
        self.inner = inner
        self.cache_dir = cache_dir
        self.ttl_s = ttl_s
        self._clock = clock

    def _path(self, area: BoundingBox) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / f"{area.south:.4f}_{area.west:.4f}_{area.north:.4f}_{area.east:.4f}.json"

    def _read(self, path: Path | None) -> tuple[float, list[Place]] | None:
        if path is None or not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            return float(record["saved_at_epoch"]), [place_from_json(p) for p in record["places"]]
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _write(self, path: Path | None, places: list[Place]) -> None:
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            record = {"saved_at_epoch": self._clock(), "places": [place_to_json(p) for p in places]}
            path.write_text(json.dumps(record), encoding="utf-8")
        except OSError:
            log.warning("could not save listings copy")

    def get_places(self, area: BoundingBox, time: datetime) -> list[Place]:
        path = self._path(area)
        saved = self._read(path)
        if saved is not None and self._clock() - saved[0] < self.ttl_s:
            return saved[1]
        try:
            places = self.inner.get_places(area, time)
        except Exception:
            if saved is not None:
                log.warning("live listings failed; using an older saved copy")
                return saved[1]
            raise
        self._write(path, places)
        return places
