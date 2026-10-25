"""Internal data shapes for the data layer. Nothing here knows about Bright Data."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BoundingBox:
    """Rectangle in degrees. Our `area` type for get_places (not in CONTRACTS yet)."""
    south: float
    west: float
    north: float
    east: float

    @property
    def center(self) -> tuple[float, float]:
        """(lat, lng)"""
        return ((self.south + self.north) / 2, (self.west + self.east) / 2)

    def contains(self, lat: float, lng: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lng <= self.east


# Weekly hours: weekday (0=Monday .. 6=Sunday) -> list of (open_minute, close_minute)
# counted from local midnight. close_minute may exceed 1440 for hours that run past
# midnight (e.g. 6 PM-2 AM is (1080, 1560)). An empty list means "closed all day".
WeeklyHours = dict[int, list[tuple[int, int]]]


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lng: float
    category: str                       # normalized: see brightdata.normalize_category
    source: str                         # "brightdata"
    fetched_at: datetime                # timezone-aware UTC
    weekly_hours: WeeklyHours | None    # None = hours missing or unreadable (unknown)
    is_24h: bool | None                 # True only if the source says open 24 hours every day
    place_id: str | None = None
    raw_category: str | None = None     # original text, for debugging only


@dataclass(frozen=True)
class RoadContext:
    """One street segment with the facts scoring needs. Scoring never sees raw OSM tags."""
    coordinates: tuple[tuple[float, float], ...]  # (lat, lng) points along the way, at least 2
    road_class: str                     # motorway|trunk|primary|secondary|tertiary|residential|
                                        # service|pedestrian|other|unknown (see osm.classify_highway)
    lit: str                            # "yes" | "no" | "unknown"; a missing tag is "unknown", never "no"
    source: str                         # "osm"
    fetched_at: datetime                # timezone-aware UTC
    osm_id: int | None = None
    name: str | None = None
    raw_highway: str | None = None      # original tag value, for debugging only


@dataclass(frozen=True)
class HelpPoint:
    type: str                           # "police" | "hospital" | "fire_station"
    lat: float
    lng: float
    source: str                         # "osm"
    fetched_at: datetime                # timezone-aware UTC
    name: str | None = None
    osm_id: int | None = None


@dataclass(frozen=True)
class AreaContext:
    roads: list[RoadContext]
    help_points: list[HelpPoint]
    fetched_at: datetime
