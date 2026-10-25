"""Transit provider interface. The GTFS reader lives in server/data/gtfs.py.

We do NOT treat a mapped bus stop as "service running": that needs a departure in the
arrival window. NoTransitProvider is the stand-in when GTFS_DIR is unset: it returns None.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from server.data.models import BoundingBox


@dataclass(frozen=True)
class ActiveStop:
    name: str
    lng: float
    lat: float
    next_departure: datetime


class TransitProvider(ABC):
    @abstractmethod
    def get_active_stops(self, area: BoundingBox, time: datetime) -> list[ActiveStop] | None:
        """Stops with service in the next ~15 minutes, or None if schedule data is unavailable."""


class NoTransitProvider(TransitProvider):
    """Used when no schedule feed is configured. Always unknown."""

    def get_active_stops(self, area: BoundingBox, time: datetime) -> list[ActiveStop] | None:
        return None
