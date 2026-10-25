"""Opening-hours parsing and evaluation. Pure functions, no network.

Timezone assumption: opening hours are the business's local wall-clock times. We
assume every place is in `PLACE_TZ` (San Francisco demo area). The arrival time is
converted into that zone before looking up the weekday and minute. A naive
arrival datetime is rejected rather than guessed.
"""
import re
from datetime import datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

from server.data.models import Place, WeeklyHours

PLACE_TZ = ZoneInfo("America/Los_Angeles")

_DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
         "friday": 4, "saturday": 5, "sunday": 6}
_DAYS.update({k[:3]: v for k, v in list(_DAYS.items())})

_TIME = r"(\d{1,2})(?:[:.](\d{2}))?\s*([ap])\.?m?\.?"
_TIME_START = r"(\d{1,2})(?:[:.](\d{2}))?\s*(?:([ap])\.?m?\.?)?"  # meridiem optional: "5-10 PM"
_RANGE = re.compile(_TIME_START + r"\s*[-–—]\s*" + _TIME, re.I)
_24H = re.compile(r"open\s*24\s*hours?|24\s*hours?", re.I)
_CLOSED = re.compile(r"^\s*closed\s*$", re.I)


class OpenStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


def _minutes(hour: str, minute: str | None, ampm: str) -> int | None:
    h, m = int(hour), int(minute or 0)
    if not (1 <= h <= 12 and 0 <= m < 60):
        return None
    h = h % 12 + (12 if ampm.lower() == "p" else 0)
    return h * 60 + m


def _parse_day_text(text: str) -> list[tuple[int, int]] | None:
    """One day's text -> intervals. None if we cannot read it."""
    if _CLOSED.match(text):
        return []
    if _24H.search(text):
        return [(0, 1440)]
    intervals = []
    for m in _RANGE.finditer(text):
        end = _minutes(m.group(4), m.group(5), m.group(6))
        if m.group(3):
            start = _minutes(m.group(1), m.group(2), m.group(3))
        else:  # "5-10 PM": start shares the end's am/pm unless that makes it start after the end
            start = _minutes(m.group(1), m.group(2), m.group(6))
            if start is not None and end is not None and start >= end:
                start = _minutes(m.group(1), m.group(2), "a" if m.group(6).lower() == "p" else "p")
        if start is None or end is None:
            return None
        if end <= start:  # runs past midnight (12 AM-12 AM also lands here = full day)
            end += 1440
        intervals.append((start, end))
    return intervals or None


def parse_weekly_hours(raw) -> tuple[WeeklyHours | None, bool | None]:
    """Raw source hours -> (weekly_hours, is_24h).

    Accepts a dict {"Monday": "9AM-5PM", ...} or a list of {"day": ..., "hours"|"time": ...}.
    Returns (None, None) if nothing is readable. A day we cannot read is left out of
    the dict (so evaluation says unknown for that day) instead of being guessed.
    """
    pairs = []
    if isinstance(raw, dict):
        pairs = list(raw.items())
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                day = item.get("day")
                hours = item.get("hours", item.get("time", item.get("open_hours")))
                pairs.append((day, hours))
    weekly: WeeklyHours = {}
    for day, text in pairs:
        if not isinstance(day, str) or day.strip().lower() not in _DAYS:
            continue
        if isinstance(text, list):
            text = ", ".join(str(t) for t in text)
        if not isinstance(text, str):
            continue
        parsed = _parse_day_text(text)
        if parsed is not None:
            weekly[_DAYS[day.strip().lower()]] = parsed
    if not weekly:
        return None, None
    is_24h = len(weekly) == 7 and all(v == [(0, 1440)] for v in weekly.values())
    return weekly, (True if is_24h else None)


def evaluate_open_status(place: Place, arrival: datetime) -> OpenStatus:
    """Is `place` open at `arrival`? Missing/unreadable hours -> UNKNOWN, never CLOSED."""
    if arrival.tzinfo is None:
        raise ValueError("arrival must be timezone-aware")
    if place.is_24h:
        return OpenStatus.OPEN
    if not place.weekly_hours:
        return OpenStatus.UNKNOWN
    local = arrival.astimezone(PLACE_TZ)
    minute = local.hour * 60 + local.minute
    today = local.weekday()
    yesterday = (local - timedelta(days=1)).weekday()
    today_hours = place.weekly_hours.get(today)
    if today_hours is None:
        return OpenStatus.UNKNOWN
    if any(s <= minute < e for s, e in today_hours):
        return OpenStatus.OPEN
    # Yesterday's late-night hours that spill past midnight into today.
    spill = place.weekly_hours.get(yesterday)
    if spill is None:
        return OpenStatus.UNKNOWN
    if any(e > 1440 and minute < e - 1440 for s, e in spill):
        return OpenStatus.OPEN
    return OpenStatus.CLOSED
