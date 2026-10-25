"""GTFS schedule reader. Public feeds only (SF Muni, BART, or any folder or .zip).

A stop counts as running only when a trip that serves it has a departure in the
arrival window, or a frequency departure that falls in that window, on a service
date that is actually running. Times at or after 24:00 belong to the next clock
day but stay on the previous service date, which is how a 1 AM trip is usually
published. A mapped stop with no trip in the window does not count.

Set GTFS_DIR (and optionally GTFS_DIR_EXTRA) to a folder or .zip. This module
never downloads a feed and never reads a secret. Times are read in
America/Los_Angeles, the demo city's local time.
"""
import csv
import io
import math
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from server.data.transit import ActiveStop

PT = ZoneInfo("America/Los_Angeles")


class TransitFeedError(RuntimeError):
    """The GTFS folder or zip could not be read. The message never includes a secret."""


class TransitUnavailable:
    """A path was set, but no feed could be read. The scorer must see this as missing."""

    failed = True


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
    headway_min: int = 1


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


def _next_departure(start: int, end: int, headway: int, q0: int, q1: int) -> int | None:
    """Earliest departure minute in [q0, q1) that also falls in [start, end)."""
    if headway <= 0 or end <= start or q1 <= q0 or q1 <= start or q0 >= end:
        return None
    if q0 <= start:
        first = start
    else:
        first = start + math.ceil((q0 - start) / headway) * headway
    if first < end and first < q1:
        return first
    return None


class _Source:
    def __init__(self, path: Path):
        self.path = path
        self._zip = None
        self._names: dict[str, str] = {}
        if path.is_dir():
            return
        if path.is_file() and zipfile.is_zipfile(path):
            self._zip = zipfile.ZipFile(path)
            self._names = {Path(name).name: name for name in self._zip.namelist()
                           if not name.startswith("__MACOSX")}
            return
        raise TransitFeedError(f"GTFS folder is missing: {path.name}")

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def rows(self, name: str) -> list[dict[str, str]]:
        if self._zip is not None:
            key = self._names.get(name)
            if key is None:
                return []
            with self._zip.open(key) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
                return list(csv.DictReader(text))
        file = self.path / name
        if not file.is_file():
            return []
        with file.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))

    def has(self, name: str) -> bool:
        if self._zip is not None:
            return name in self._names
        return (self.path / name).is_file()


class TransitSchedule:
    """In-memory schedule. active_stops is pure: it does not fetch."""

    def __init__(self, stops: dict[str, _Stop], visits: list[_Visit], services: dict[str, _Service],
                 frequencies: list[_Freq], zone: ZoneInfo = PT):
        self.stops = stops
        self.visits = visits
        self.services = services
        self.frequencies = frequencies
        self.zone = zone
        self._cache: dict[tuple, list[ActiveStop]] = {}

    def active_stops(self, when: datetime, window_min: int) -> list[ActiveStop]:
        if when.tzinfo is None:
            raise ValueError("arrival must be timezone-aware")
        local = when.astimezone(self.zone)
        key = (local.date().isoformat(), local.hour, local.minute, int(window_min))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        found: dict[str, datetime] = {}
        for service_day, minute in ((local.date(), local.hour * 60 + local.minute),
                                    ((local - timedelta(days=1)).date(), local.hour * 60 + local.minute + 1440)):
            self._collect(service_day, minute, minute + int(window_min), found)
        out = []
        for stop_id, depart in sorted(found.items(), key=lambda item: (item[1], item[0])):
            stop = self.stops.get(stop_id)
            if stop is not None:
                out.append(ActiveStop(stop.name or stop_id, stop.lng, stop.lat, depart))
        self._cache[key] = out
        return out

    def _collect(self, service_day, start_min: int, end_min: int, found: dict[str, datetime]) -> None:
        running = {sid for sid, svc in self.services.items() if svc.runs_on(service_day)}
        if not running:
            return
        base = datetime(service_day.year, service_day.month, service_day.day, tzinfo=self.zone)
        for visit in self.visits:
            if visit.service_id not in running or not start_min <= visit.depart_min < end_min:
                continue
            self._keep(found, visit.stop_id, base + timedelta(minutes=visit.depart_min))
        for freq in self.frequencies:
            if freq.service_id not in running:
                continue
            depart_min = _next_departure(freq.start_min, freq.end_min, max(1, freq.headway_min),
                                         start_min, end_min)
            if depart_min is None:
                continue
            depart = base + timedelta(minutes=depart_min)
            for stop_id in freq.stop_ids:
                self._keep(found, stop_id, depart)

    @staticmethod
    def _keep(found: dict[str, datetime], stop_id: str, depart: datetime) -> None:
        prev = found.get(stop_id)
        if prev is None or depart < prev:
            found[stop_id] = depart


class CombinedSchedule:
    """Two public feeds (for example Muni and BART) asked as one schedule."""

    def __init__(self, parts: list[TransitSchedule]):
        self.parts = parts

    def active_stops(self, when: datetime, window_min: int) -> list[ActiveStop]:
        found: dict[tuple, ActiveStop] = {}
        for part in self.parts:
            for stop in part.active_stops(when, window_min):
                key = (stop.name, round(stop.lat, 5), round(stop.lng, 5))
                prev = found.get(key)
                if prev is None or stop.next_departure < prev.next_departure:
                    found[key] = stop
        return list(found.values())


def load_gtfs(folder: Path) -> TransitSchedule:
    source = _Source(Path(folder))
    try:
        return _load(source)
    finally:
        source.close()


def _load(source: _Source) -> TransitSchedule:
    for required in ("stops.txt", "trips.txt", "stop_times.txt"):
        if not source.has(required):
            raise TransitFeedError(f"GTFS feed is missing {required}")
    stops: dict[str, _Stop] = {}
    for row in source.rows("stops.txt"):
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
    for row in source.rows("calendar.txt"):
        sid = (row.get("service_id") or "").strip()
        if not sid:
            continue
        svc = service(sid)
        svc.days = tuple(row.get(name, "0").strip() == "1" for name in day_names)
        svc.start = (row.get("start_date") or "").strip()
        svc.end = (row.get("end_date") or "").strip()
    for row in source.rows("calendar_dates.txt"):
        sid = (row.get("service_id") or "").strip()
        ymd = (row.get("date") or "").strip()
        kind = (row.get("exception_type") or "").strip()
        if not sid or not ymd:
            continue
        svc = service(sid)
        if kind == "2":
            svc.removed.add(ymd)
        elif kind == "1":
            svc.added.add(ymd)
    if not services:
        raise TransitFeedError("GTFS feed has no calendar or calendar_dates")
    trip_service = {}
    for row in source.rows("trips.txt"):
        trip_id = (row.get("trip_id") or "").strip()
        sid = (row.get("service_id") or "").strip()
        if trip_id and sid:
            trip_service[trip_id] = sid
    freq_trips: dict[str, list[tuple[int, int, int]]] = {}
    for row in source.rows("frequencies.txt"):
        trip_id = (row.get("trip_id") or "").strip()
        start, end = _minutes(row.get("start_time") or ""), _minutes(row.get("end_time") or "")
        try:
            headway_secs = int((row.get("headway_secs") or "").strip())
        except ValueError:
            continue
        if not trip_id or start is None or end is None or end <= start or headway_secs <= 0:
            continue
        freq_trips.setdefault(trip_id, []).append((start, end, max(1, round(headway_secs / 60))))
    trip_offsets: dict[str, list[tuple[str, int]]] = {}
    visits: list[_Visit] = []
    for row in source.rows("stop_times.txt"):
        trip_id = (row.get("trip_id") or "").strip()
        stop_id = (row.get("stop_id") or "").strip()
        sid = trip_service.get(trip_id)
        minute = _minutes(row.get("departure_time") or row.get("arrival_time") or "")
        if not sid or not stop_id or stop_id not in stops or minute is None:
            continue
        if trip_id in freq_trips:
            trip_offsets.setdefault(trip_id, []).append((stop_id, minute))
            continue
        visits.append(_Visit(stop_id, sid, minute))
    frequencies: list[_Freq] = []
    for trip_id, windows in freq_trips.items():
        sid = trip_service.get(trip_id)
        offsets = trip_offsets.get(trip_id) or []
        if not sid or not offsets:
            continue
        first = min(minute for _stop, minute in offsets)
        for stop_id, minute in offsets:
            shift = minute - first
            for start, end, headway in windows:
                frequencies.append(_Freq(sid, (stop_id,), start + shift, end + shift, headway))
    if not stops or not (visits or frequencies):
        raise TransitFeedError("GTFS feed has no usable stops and trip times")
    return TransitSchedule(stops, visits, services, frequencies)
