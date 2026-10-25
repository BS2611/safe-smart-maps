"""Street photos from Mapillary (crowd-sourced, CC BY-SA 4.0). Implements `PhotoSource` for the auditor.

Photos can be years old and are usually taken in daytime, so every use is labeled that way. The token
is read from MAPILLARY_TOKEN and never appears in messages. Any failure means "no photo" (None).
"""
import math
import os
from datetime import datetime, timezone

import httpx

from server.services.audit import Photo

API = "https://graph.mapillary.com/images"
ATTRIBUTION = "Photo: Mapillary contributors, CC BY-SA 4.0"
FIELDS = "id,captured_at,is_pano,computed_geometry,thumb_1024_url"
M_PER_DEG = 111_195


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dy = (lat2 - lat1) * M_PER_DEG
    dx = (lng2 - lng1) * M_PER_DEG * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def pick_best(images: list[dict], lat: float, lng: float, max_age_years: float, now: datetime) -> dict | None:
    """Nearest flat (non-panorama) photo no older than max_age_years; ties go to the newer one."""
    best, best_key = None, None
    for img in images:
        coords = (img.get("computed_geometry") or {}).get("coordinates")
        if img.get("is_pano") or not coords or not img.get("thumb_1024_url") or not img.get("captured_at"):
            continue
        taken = datetime.fromtimestamp(img["captured_at"] / 1000, tz=timezone.utc)
        if (now - taken).days > max_age_years * 365:
            continue
        key = (round(_distance_m(lat, lng, coords[1], coords[0])), -img["captured_at"])
        if best_key is None or key < best_key:
            best, best_key = img, key
    return best


class MapillaryPhotoSource:
    def __init__(self, token: str | None = None, radius_m: float = 40.0, max_age_years: float = 5.0,
                 timeout_s: float = 15.0, client: httpx.Client | None = None):
        self._token = token
        self.radius_m = radius_m
        self.max_age_years = max_age_years
        self.timeout_s = timeout_s
        self._client = client

    def _token_value(self) -> str | None:
        return self._token or os.environ.get("MAPILLARY_TOKEN") or None

    def find(self, lat: float, lng: float, now: datetime | None = None) -> dict | None:
        """Metadata of the best photo near the point, or None. Never raises."""
        token = self._token_value()
        if not token:
            return None
        dlat = self.radius_m / M_PER_DEG
        dlng = dlat / max(0.2, math.cos(math.radians(lat)))
        bbox = f"{lng - dlng:.6f},{lat - dlat:.6f},{lng + dlng:.6f},{lat + dlat:.6f}"
        try:
            resp = (self._client or httpx).get(API, params={"access_token": token, "bbox": bbox, "limit": 25,
                                                            "fields": FIELDS}, timeout=self.timeout_s)
            if resp.status_code != 200:
                return None
            images = resp.json().get("data", [])
        except (httpx.HTTPError, ValueError, AttributeError):
            return None
        return pick_best(images, lat, lng, self.max_age_years, now or datetime.now(timezone.utc))

    def photo_near(self, lat: float, lng: float) -> Photo | None:
        img = self.find(lat, lng)
        if img is None:
            return None
        try:
            resp = (self._client or httpx).get(img["thumb_1024_url"], timeout=self.timeout_s)
            if resp.status_code != 200 or not resp.content:
                return None
        except httpx.HTTPError:
            return None
        taken = datetime.fromtimestamp(img["captured_at"] / 1000, tz=timezone.utc).date().isoformat()
        return Photo(id=str(img["id"]), jpeg=resp.content, captured_at=taken, attribution=ATTRIBUTION)
