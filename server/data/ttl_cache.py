"""Small in-memory TTL cache for data that is cheap to hold and slow to fetch (e.g. the OSM area
context). The places cache is a different thing: see cache.py (file cache, never fetches on a route request).
"""
import threading
import time
from collections.abc import Callable, Hashable
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: float = 900.0, clock: Callable[[], float] = time.monotonic,
                 max_items: int = 256):
        self.ttl = ttl_seconds
        self._clock = clock
        self._max = max_items
        self._items: dict[Hashable, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: Hashable) -> tuple[bool, Any]:
        with self._lock:
            entry = self._items.get(key)
            if entry is not None and self._clock() - entry[0] < self.ttl:
                self.hits += 1
                return True, entry[1]
            if entry is not None:
                del self._items[key]
            self.misses += 1
            return False, None

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            if len(self._items) >= self._max and key not in self._items:
                oldest = min(self._items, key=lambda k: self._items[k][0])
                del self._items[oldest]
            self._items[key] = (self._clock(), value)

    def get_or_load(self, key: Hashable, loader: Callable[[], Any]) -> Any:
        """Return the cached value, or call `loader`, cache and return it.
        Failures are NOT cached (an exception from `loader` propagates)."""
        hit, value = self.get(key)
        if hit:
            return value
        value = loader()
        self.set(key, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
