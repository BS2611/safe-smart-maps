"""Bright Data places provider (Web Scraper API, Google Maps "discover by location").

Raw Bright Data fields are read ONLY in this file and converted to `Place`.
Credentials come from environment variables and are never logged.
"""
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from server.data.models import BoundingBox, Place
from server.data.opening_hours import parse_weekly_hours
from server.data.places import PlacesProvider

API_BASE = "https://api.brightdata.com/datasets/v3"
SCRAPE_URL = f"{API_BASE}/scrape"
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
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None  # "nan" / "inf" are not coordinates


def normalize_record(rec: dict, fetched_at: datetime) -> Place | None:
    """One raw Bright Data record -> Place, or None if unusable (no name/coords)."""
    if not isinstance(rec, dict) or rec.get("error"):
        return None
    name = rec.get("name")
    # live Google Maps records use lat/lon; latitude/longitude kept as a fallback
    lat = _to_float(rec.get("lat", rec.get("latitude")))
    lng = _to_float(rec.get("lon", rec.get("longitude")))
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
                 limit_per_keyword: int = 20, timeout_s: float = 180.0,
                 max_wait_s: float = 300.0, poll_interval_s: float = 5.0):
        self.keywords = keywords
        self.zoom_level = zoom_level
        self.limit_per_keyword = limit_per_keyword
        self.timeout_s = timeout_s
        self.max_wait_s = max_wait_s
        self.poll_interval_s = poll_interval_s

    def _wait_for_snapshot(self, resp, api_key: str):
        """Sync scrape ran long (HTTP 202 + snapshot_id): poll progress, then download."""
        try:
            snapshot_id = json.loads(resp.text)["snapshot_id"]
        except (ValueError, KeyError, TypeError):
            raise BrightDataError("Bright Data answered 202 without a snapshot_id") from None
        headers = {"Authorization": f"Bearer {api_key}"}
        deadline = time.monotonic() + self.max_wait_s
        try:
            while True:
                prog = httpx.get(f"{API_BASE}/progress/{snapshot_id}", headers=headers, timeout=30)
                status = json.loads(prog.text).get("status") if prog.status_code == 200 else None
                if status == "ready":
                    break
                if status == "failed" or prog.status_code in (401, 403, 404):
                    raise BrightDataError(f"Bright Data snapshot {status or prog.status_code}")
                if time.monotonic() >= deadline:
                    raise BrightDataError("Bright Data snapshot not ready before max_wait_s")
                time.sleep(self.poll_interval_s)
            return httpx.get(f"{API_BASE}/snapshot/{snapshot_id}", params={"format": "json"},
                             headers=headers, timeout=self.timeout_s)
        except (httpx.HTTPError, ValueError) as e:
            raise BrightDataError(f"Bright Data snapshot request failed: {type(e).__name__}") from None

    def get_places(self, area: BoundingBox, time: datetime) -> list[Place]:
        """Live places inside `area`. `time` is not used for fetching (listings are not
        time-specific); callers apply evaluate_open_status(place, time) afterwards."""
        api_key = os.environ.get("BRIGHTDATA_API_KEY")
        if not api_key:
            raise BrightDataError("BRIGHTDATA_API_KEY is not set")
        dataset_id = os.environ.get("BRIGHTDATA_PLACES_DATASET_ID") or DEFAULT_DATASET_ID  # blank in .env = unset
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
            resp = self._wait_for_snapshot(resp, api_key)
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
