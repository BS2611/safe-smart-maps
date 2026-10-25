"""Street-stretch auditor: Claude looks at one street photo and reports what is visible.

Rules (see DECISIONS.md): the result is a clearly labeled, DAYTIME-photo signal. It never replaces
hard data, never says a street is safe, and any failure or odd answer returns None (= not sure).
Photos come from a `PhotoSource` (none is wired yet; Mapillary is planned), so this module is
testable with fixtures and costs nothing until a source and an API key exist.
"""
import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from server.services.explain import ANTHROPIC_URL, DEFAULT_MODEL
from server.services.wording import find_banned_wording

LABEL = "Seen in a street photo (daytime, may be old); Claude's reading, not a measurement"
YES_NO = {"yes", "no", "unclear"}
SIDEWALK = {"good", "poor", "unclear"}
CONFIDENCE = {"low", "medium", "high"}
SYSTEM_PROMPT = (
    "You look at one street-level photo and describe only what is visible. Reply with ONE JSON object "
    'and nothing else, with keys: "streetlights_visible" ("yes"|"no"|"unclear"), "open_storefronts" '
    '("yes"|"no"|"unclear"), "sidewalk_visibility" ("good"|"poor"|"unclear"), "construction" '
    '("yes"|"no"|"unclear"), "confidence" ("low"|"medium"|"high"), "evidence" (one plain sentence, '
    "under 200 characters, describing what you see). The photo may be taken in daytime; do not guess "
    "about night. Never say a place is safe or dangerous. If the image is unclear, use "
    '"unclear" and confidence "low".'
)


@dataclass(frozen=True)
class Photo:
    id: str
    jpeg: bytes
    captured_at: str | None = None
    attribution: str = ""


class PhotoSource(Protocol):
    def photo_near(self, lat: float, lng: float) -> Photo | None: ...


@dataclass(frozen=True)
class StretchAudit:
    photo_id: str
    streetlights_visible: str
    open_storefronts: str
    sidewalk_visibility: str
    construction: str
    confidence: str
    evidence: str
    captured_at: str | None
    attribution: str
    label: str = LABEL

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def parse_audit(text: str, photo: Photo) -> StretchAudit | None:
    """Strict check of the model's JSON. Anything off returns None."""
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    evidence = data.get("evidence")
    checks = (data.get("streetlights_visible") in YES_NO, data.get("open_storefronts") in YES_NO,
              data.get("sidewalk_visibility") in SIDEWALK, data.get("construction") in YES_NO,
              data.get("confidence") in CONFIDENCE,
              isinstance(evidence, str) and 0 < len(evidence.strip()) <= 300)
    if not all(checks) or find_banned_wording(evidence):
        return None
    return StretchAudit(photo.id, data["streetlights_visible"], data["open_storefronts"],
                        data["sidewalk_visibility"], data["construction"], data["confidence"],
                        evidence.strip(), photo.captured_at, photo.attribution)


class StreetAuditor:
    """One Claude vision call per photo, cached by photo id, capped per instance."""

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout_s: float = 20.0,
                 max_calls: int | None = None, client: httpx.Client | None = None):
        self._api_key = api_key
        self.model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self.timeout_s = timeout_s
        env_cap = os.environ.get("AUDIT_MAX_CALLS_PER_REQUEST", "")
        self.max_calls = max_calls if max_calls is not None else (int(env_cap) if env_cap.isdigit() else 3)
        self._client = client
        self._cache: dict[str, StretchAudit | None] = {}
        self.calls = 0

    def audit(self, photo: Photo) -> StretchAudit | None:
        """Never raises. None = not sure (no key, cap reached, error, or an answer we do not trust)."""
        if photo.id in self._cache:
            return self._cache[photo.id]
        api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key or self.calls >= self.max_calls:
            return None
        self.calls += 1
        body = {
            "model": self.model, "max_tokens": 300, "thinking": {"type": "disabled"},
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                              "data": base64.b64encode(photo.jpeg).decode()}},
                {"type": "text", "text": "Describe this street photo as instructed."}]}],
        }
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        result = None
        try:
            resp = (self._client or httpx).post(ANTHROPIC_URL, json=body, headers=headers,
                                                timeout=self.timeout_s)
            if resp.status_code == 200:
                text = "".join(b.get("text", "") for b in resp.json().get("content", [])
                               if b.get("type") == "text")
                result = parse_audit(text, photo)
        except (httpx.HTTPError, ValueError):
            result = None
        self._cache[photo.id] = result
        return result

    def audit_near(self, source: PhotoSource | None, lat: float, lng: float) -> StretchAudit | None:
        photo = source.photo_near(lat, lng) if source is not None else None
        return self.audit(photo) if photo is not None else None
