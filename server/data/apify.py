"""Apify places fallback (actor compass/crawler-google-places). Used ONLY when Bright Data fails.

Raw Apify fields are read only in this file and converted to `Place`. The token comes from APIFY_TOKEN
and never appears in messages. A run costs money (about $1.50 per 1,000 places), so the number of
places per run is capped by `limit_per_keyword` x number of keywords.
"""
import os
import re
from datetime import datetime, timezone

import httpx

from server.data.brightdata import normalize_category
from server.data.models import BoundingBox, Place
from server.data.opening_hours import parse_weekly_hours
from server.data.places import PlacesProvider

RUN_URL = "https://api.apify.com/v2/acts/compass~crawler-google-places/run-sync-get-dataset-items"
DEFAULT_KEYWORDS = ("restaurant", "cafe", "convenience store")


class ApifyError(RuntimeError):
    """Messages never contain the token."""


def _clean_hours(text):
    """'8 AM to 2:30 PM' (with narrow no-break spaces) -> '8 AM-2:30 PM', which the shared parser reads."""
    if not isinstance(text, str):
        return text
    text = text.replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+to\s+", "-", text, flags=re.I)


def normalize_record(rec: dict, fetched_at: datetime) -> Place | None:
    """One raw Apify item -> Place, or None if unusable or closed for good."""
    if not isinstance(rec, dict) or rec.get("permanentlyClosed") or rec.get("temporarilyClosed"):
        return None
    loc = rec.get("location") or {}
    name, lat, lng = rec.get("title"), loc.get("lat"), loc.get("lng")
    if not isinstance(name, str) or not name.strip() or not isinstance(lat, (int, float)) \
            or not isinstance(lng, (int, float)):
        return None
    hours = rec.get("openingHours")
    if isinstance(hours, list):
        hours = [{**h, "hours": _clean_hours(h.get("hours"))} for h in hours if isinstance(h, dict)]
    weekly, is_24h = parse_weekly_hours(hours)
    raw_cat = rec.get("categoryName")
    return Place(name=name.strip(), lat=float(lat), lng=float(lng), category=normalize_category(raw_cat),
                 source="apify", fetched_at=fetched_at, weekly_hours=weekly, is_24h=is_24h,
                 place_id=str(rec["placeId"]) if rec.get("placeId") else None,
                 raw_category=raw_cat if isinstance(raw_cat, str) else None)


class ApifyPlacesProvider(PlacesProvider):
    def __init__(self, keywords=DEFAULT_KEYWORDS, limit_per_keyword: int = 20, timeout_s: float = 180.0,
                 client: httpx.Client | None = None):
        self.keywords = keywords
        self.limit_per_keyword = limit_per_keyword
        self.timeout_s = timeout_s
        self._client = client

    @staticmethod
    def configured() -> bool:
        return bool(os.environ.get("APIFY_TOKEN"))

    def get_places(self, area: BoundingBox, time: datetime) -> list[Place]:
        token = os.environ.get("APIFY_TOKEN")
        if not token:
            raise ApifyError("APIFY_TOKEN is not set")
        ring = [[area.west, area.south], [area.east, area.south], [area.east, area.north],
                [area.west, area.north], [area.west, area.south]]
        body = {"searchStringsArray": list(self.keywords), "maxCrawledPlacesPerSearch": self.limit_per_keyword,
                "language": "en", "scrapePlaceDetailPage": False,
                "customGeolocation": {"type": "Polygon", "coordinates": [ring]}}
        try:
            resp = (self._client or httpx).post(
                RUN_URL, params={"format": "json", "timeout": int(self.timeout_s) - 20},
                headers={"Authorization": f"Bearer {token}"}, json=body, timeout=self.timeout_s)
        except httpx.HTTPError as e:
            raise ApifyError(f"Apify request failed: {type(e).__name__}") from None
        if resp.status_code not in (200, 201):
            raise ApifyError(f"Apify answered HTTP {resp.status_code}")
        try:
            items = resp.json()
        except ValueError:
            raise ApifyError("Apify sent an unreadable answer") from None
        if not isinstance(items, list):
            raise ApifyError("Apify answered with an unexpected shape")
        fetched = datetime.now(timezone.utc)
        seen, places = set(), []
        for rec in items:
            p = normalize_record(rec, fetched)
            if p is None or not area.contains(p.lat, p.lng):
                continue
            key = p.place_id or (p.name, p.lat, p.lng)
            if key not in seen:
                seen.add(key)
                places.append(p)
        return places


class FallbackPlacesProvider(PlacesProvider):
    """Tries `primary`; only if it raises does it try `secondary`. Never both for the same fetch."""

    def __init__(self, primary: PlacesProvider, secondary: PlacesProvider, secondary_ready=lambda: True):
        self.primary, self.secondary, self.secondary_ready = primary, secondary, secondary_ready
        self.last_source = "primary"

    def get_places(self, area: BoundingBox, time: datetime) -> list[Place]:
        try:
            places = self.primary.get_places(area, time)
            self.last_source = "primary"
            return places
        except Exception:
            if not self.secondary_ready():
                raise
            places = self.secondary.get_places(area, time)
            self.last_source = "secondary"
            return places
