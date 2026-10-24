"""Bright Data places provider (Web Scraper API, Google Maps "discover by location").

Raw Bright Data fields are read ONLY in this file and converted to `Place`.
Credentials come from environment variables and are never logged.
"""
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from server.data.models import BoundingBox, Place
from server.data.opening_hours import parse_weekly_hours
from server.data.places import PlacesProvider

SCRAPE_URL = "https://api.brightdata.com/datasets/v3/scrape"
DEFAULT_DATASET_ID = "gd_m8ebnr0q2qlklc02fz"  # Google Maps places (public dataset id)
DEFAULT_KEYWORDS = ("restaurant", "cafe", "convenience store")

# Normalized category <- words found in the raw category text. First match wins.
_CATEGORY_WORDS = [
    ("restaurant", ("restaurant", "diner", "pizza", "bistro", "eatery", "grill")),
    ("cafe", ("cafe", "café", "coffee", "bakery", "tea")),
    ("bar", ("bar", "pub", "brewery", "lounge")),
    ("convenience_store", ("convenience", "grocery", "supermarket", "market", "liquor")),
    ("pharmacy", ("pharmacy", "drugstore")),
    ("gas_station", ("gas station", "fuel")),
]


class BrightDataError(RuntimeError):
    """Raised for config or upstream problems. Messages never contain credentials."""


def normalize_category(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "other"
    text = raw.lower()
    for name, words in _CATEGORY_WORDS:
        # whole words only, so "steakhouse" is not "tea" and "barber" is not "bar"
        if any(re.search(rf"\b{re.escape(w)}s?\b", text) for w in words):
            return name
    return "other"


def _to_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def normalize_record(rec: dict, fetched_at: datetime) -> Place | None:
    """One raw Bright Data record -> Place, or None if unusable (no name/coords)."""
    if not isinstance(rec, dict) or rec.get("error"):
        return None
    name = rec.get("name")
    lat, lng = _to_float(rec.get("latitude")), _to_float(rec.get("longitude"))
    if not isinstance(name, str) or not name.strip() or lat is None or lng is None:
        return None
    weekly, is_24h = parse_weekly_hours(rec.get("open_hours"))
    raw_cat = rec.get("category")
    return Place(
        name=name.strip(), lat=lat, lng=lng,
        category=normalize_category(raw_cat), source="brightdata",
        fetched_at=fetched_at, weekly_hours=weekly, is_24h=is_24h,
        place_id=str(rec["place_id"]) if rec.get("place_id") else None,
        raw_category=raw_cat if isinstance(raw_cat, str) else None,
    )


def _parse_response_body(text: str) -> list[dict]:
    """The API returns a JSON array, or newline-delimited JSON. Accept both."""
    text = text.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


class BrightDataPlacesProvider(PlacesProvider):
    def __init__(self, keywords=DEFAULT_KEYWORDS, zoom_level: int = 16,
                 limit_per_keyword: int = 20, timeout_s: float = 90.0):
        self.keywords = keywords
        self.zoom_level = zoom_level
        self.limit_per_keyword = limit_per_keyword
        self.timeout_s = timeout_s

    def get_places(self, area: BoundingBox, time: datetime) -> list[Place]:
        """Live places inside `area`. `time` is not used for fetching (listings are not
        time-specific); callers apply evaluate_open_status(place, time) afterwards."""
        api_key = os.environ.get("BRIGHTDATA_API_KEY")
        if not api_key:
            raise BrightDataError("BRIGHTDATA_API_KEY is not set")
        dataset_id = os.environ.get("BRIGHTDATA_PLACES_DATASET_ID", DEFAULT_DATASET_ID)
        lat, lng = area.center
        body = {
            "input": [{"country": "US", "lat": lat, "long": lng,
                       "zoom_level": self.zoom_level, "keyword": k} for k in self.keywords],
            "limit_per_input": self.limit_per_keyword,
        }
        params = {"dataset_id": dataset_id, "type": "discover_new",
                  "discover_by": "location", "include_errors": "true"}
        try:
            resp = httpx.post(SCRAPE_URL, params=params, json=body, timeout=self.timeout_s,
                              headers={"Authorization": f"Bearer {api_key}"})
        except httpx.HTTPError as e:
            raise BrightDataError(f"Bright Data request failed: {type(e).__name__}") from None
        if resp.status_code == 202:
            raise BrightDataError("Bright Data answered 202 (async job); sync scrape did not finish in time")
        if resp.status_code != 200:
            raise BrightDataError(f"Bright Data returned HTTP {resp.status_code}")
        try:
            records = _parse_response_body(resp.text)
        except json.JSONDecodeError:
            raise BrightDataError("Bright Data response was not valid JSON") from None

        fetched_at = datetime.now(timezone.utc)
        places: dict[str, Place] = {}
        for rec in records:
            p = normalize_record(rec, fetched_at)
            if p is None or not area.contains(p.lat, p.lng):
                continue
            places[p.place_id or f"{p.name}|{p.lat}|{p.lng}"] = p  # dedupe across keywords
        return list(places.values())
