"""GTFS schedule reader. Public feeds only (SF Muni, BART, or any folder of GTFS text files).

A stop counts as running only when a trip that serves it has a departure in the
arrival window, or a frequency window that covers that minute, on a service date
that is actually running. A mapped stop with no trip in the window does not count.

Set GTFS_DIR to an extracted feed (stops.txt, trips.txt, stop_times.txt, calendar.txt).
calendar_dates.txt and frequencies.txt are optional. This module never downloads a feed.
"""
import csv
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from server.data.transit import ActiveStop

PT = ZoneInfo("America/Los_Angeles")


class TransitFeedError(RuntimeError):
    """The GTFS folder could not be read. The message never includes a secret."""


@dataclass(frozen=True)
class _Stop:
    stop_id: str
    name: str
    lat: float
    lng: float


@dataclass(frozen=True)
class _Visit:
    stop_id: str
    service_id: str
    depart_min: int


@dataclass(frozen=True)
class _Freq:
    service_id: str
    stop_ids: tuple[str, ...]
    start_min: int
    end_min: int


@dataclass
class _Service:
    days: tuple[bool, ...] = (False,) * 7
    start: str = ""
    end: str = ""
    added: set[str] = field(default_factory=set)
    removed: set[str] = field(default_factory=set)

    def runs_on(self, day) -> bool:
        ymd = day.strftime("%Y%m%d")
        if ymd in self.removed:
            return False
        if ymd in self.added:
            return True
        if not self.start or not (self.start <= ymd <= self.end):
            return False
        return self.days[day.weekday()]


def _minutes(value: str) -> int | None:
    parts = (value or "").strip().split(":")
    if len(parts) < 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if hour < 0 or not 0 <= minute < 60:
        return None
    return hour * 60 + minute


def _rows(folder: Path, name: str) -> list[dict[str, str]]:
    path = folder / name
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


class TransitSchedule:
    """In-memory schedule. active_stops is pure: it does not fetch."""

    def __init__(self, stops: dict[str, _Stop], visits: list[_Visit], services: dict[str, _Service],
                 frequencies: list[_Freq]):
        self.stops = stops
        self.visits = visits
        self.services = services
        self.frequencies = frequencies

    def active_stops(self, when: datetime, window_min: int) -> list[ActiveStop]:
        if when.tzinfo is None:
            raise ValueError("arrival must be timezone-aware")
        local = when.astimezone(PT)
        found: dict[str, datetime] = {}
        for service_day, minute in ((local.date(), local.hour * 60 + local.minute),
                                    ((local - timedelta(days=1)).date(), local.hour * 60 + local.minute + 1440)):
            self._collect(service_day, minute, minute + window_min, found)
        out = []
        for stop_id, depart in sorted(found.items(), key=lambda item: item[1]):
            stop = self.stops.get(stop_id)
            if stop is not None:
                out.append(ActiveStop(stop.name or stop_id, stop.lng, stop.lat, depart))
        return out

    def _collect(self, service_day, start_min: int, end_min: int, found: dict[str, datetime]) -> None:
        running = {sid for sid, svc in self.services.items() if svc.runs_on(service_day)}
        if not running:
            return
        base = datetime(service_day.year, service_day.month, service_day.day, tzinfo=PT)
        for visit in self.visits:
            if visit.service_id not in running or not start_min <= visit.depart_min < end_min:
                continue
            depart = base + timedelta(minutes=visit.depart_min)
            prev = found.get(visit.stop_id)
            if prev is None or depart < prev:
                found[visit.stop_id] = depart
        for freq in self.frequencies:
            if freq.service_id not in running or freq.end_min <= start_min or freq.start_min >= end_min:
                continue
            depart = base + timedelta(minutes=max(freq.start_min, start_min))
            for stop_id in freq.stop_ids:
                prev = found.get(stop_id)
                if prev is None or depart < prev:
                    found[stop_id] = depart


def load_gtfs(folder: Path) -> TransitSchedule:
    folder = Path(folder)
    if not folder.is_dir():
        raise TransitFeedError(f"GTFS folder is missing: {folder.name}")
    for required in ("stops.txt", "trips.txt", "stop_times.txt"):
        if not (folder / required).is_file():
            raise TransitFeedError(f"GTFS feed is missing {required}")
    stops: dict[str, _Stop] = {}
    for row in _rows(folder, "stops.txt"):
        try:
            lat, lng = float(row.get("stop_lat", "")), float(row.get("stop_lon", ""))
        except ValueError:
            continue
        stop_id = (row.get("stop_id") or "").strip()
        if stop_id and -90 <= lat <= 90 and -180 <= lng <= 180:
            stops[stop_id] = _Stop(stop_id, (row.get("stop_name") or stop_id).strip(), lat, lng)
    services: dict[str, _Service] = {}

    def service(sid: str) -> _Service:
        return services.setdefault(sid, _Service())

    day_names = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    for row in _rows(folder, "calendar.txt"):
        sid = (row.get("service_id") or "").strip()
        if not sid:
            continue
        svc = service(sid)
        svc.days = tuple(row.get(name, "0").strip() == "1" for name in day_names)
        svc.start = (row.get("start_date") or "").strip()
        svc.end = (row.get("end_date") or "").strip()
    for row in _rows(folder, "calendar_dates.txt"):
        sid = (row.get("service_id") or "").strip()
        ymd = (row.get("date") or "").strip()
        if not sid or not ymd:
            continue
        svc = service(sid)
        if (row.get("exception_type") or "").strip() == "2":
            svc.removed.add(ymd)
        else:
            svc.added.add(ymd)
    trip_service = {}
    for row in _rows(folder, "trips.txt"):
        trip_id = (row.get("trip_id") or "").strip()
        sid = (row.get("service_id") or "").strip()
        if trip_id and sid:
            trip_service[trip_id] = sid
    trip_stops: dict[str, list[str]] = {}
    visits: list[_Visit] = []
    for row in _rows(folder, "stop_times.txt"):
        trip_id = (row.get("trip_id") or "").strip()
        stop_id = (row.get("stop_id") or "").strip()
        sid = trip_service.get(trip_id)
        minute = _minutes(row.get("departure_time") or row.get("arrival_time") or "")
        if not sid or not stop_id or stop_id not in stops or minute is None:
            continue
        visits.append(_Visit(stop_id, sid, minute))
        trip_stops.setdefault(trip_id, [])
        if stop_id not in trip_stops[trip_id]:
            trip_stops[trip_id].append(stop_id)
    frequencies: list[_Freq] = []
    for row in _rows(folder, "frequencies.txt"):
        trip_id = (row.get("trip_id") or "").strip()
        sid = trip_service.get(trip_id)
        start, end = _minutes(row.get("start_time") or ""), _minutes(row.get("end_time") or "")
        if not sid or start is None or end is None or end <= start:
            continue
        frequencies.append(_Freq(sid, tuple(trip_stops.get(trip_id, ())), start, end))
    if not stops or not (visits or frequencies):
        raise TransitFeedError("GTFS feed has no usable stops and trip times")
    return TransitSchedule(stops, visits, services, frequencies)
