# CONTRACTS - formats and interfaces both sides rely on

SOURCE OF TRUTH. `docs/specs/TECHNICAL_SPEC.md` must match this file; if they
disagree, this file wins and the spec gets fixed. If you change anything here,
update this file in the same commit and log it (field "Contracts affected").
Status: DRAFT v1 + additive changes below (marked "added 24 Oct"). Amey must confirm. The code in server/ implements this file; tests/fixtures/routes_response*.json are generated from it (python -m tests.make_fixture).

## Folder layout (repo root = this folder)
- `web/`      Next.js responsive PWA for Android + iOS browsers (Bhavpreet)
- `watch/`    Wear OS (Samsung) companion app, Kotlin, stretch (owner TBD)
- `server/`   Python backend, 3 layers (Amey): `api/` (HTTP) -> `services/` (scoring, routes, explain) -> `data/` (providers, cache)
- `scoring/`  `scoring_v1.json` weights and thresholds
- `tests/fixtures/` labeled test fixtures only (never in the live demo path)

## Versioning
Every response has `api_version` ("1") and `scoring_version` ("scoring_v1").
Add fields freely; never remove or rename a field within a version.

## Segment score (backend -> frontend)
```json
{
  "segment_id": "string",
  "start": [lng, lat],
  "end": [lng, lat],
  "length_m": 50,
  "arrival_time": "2026-10-24T23:10:00-07:00",
  "score": 0,                                   (null when confidence is "unknown")
  "band": "green | yellow | red | unknown",
  "factors": { "open_places": 0,   (each factor is a number 0-100 or null = not sure) "lighting": 0, "main_road": 0,
               "help_points": 0, "transit": 0, "activity_estimate": 0,
               "incidents": 0, "turns": 0 },
  "reasons": ["2 open places within 50 m", "lit main road"],
  "data_fetched_at": "ISO time",
  "confidence": "high | low | unknown"
}
```
`confidence: unknown` (or a missing factor) must render as "not sure".

## Route result
```json
{
  "label": "safest | balanced | fastest",
  "route_id": "r1a2b3c4d5e",                   (added 24 Oct: stable id from the geometry)
  "via": ["Polk St", "Market St"],             (added 24 Oct: longest named streets, route order)
  "also_labels": [],
  "duration_min": 0,
  "extra_min": 0,
  "distance_m": 0,
  "route_score": 0,
  "continuity": { "coverage_pct": 0, "longest_gap_m": 0,
                  "longest_gap_note": "near the park", "worst_window_score": 0 },
  "open_places_count": 0,                      (null when live listings were unavailable)
  "nearest_help_point": { "name": "string", "distance_m": 0 },
  "geometry": "GeoJSON LineString",
  "segments": ["Segment score"],
  "explanation": "plain-language text from the Claude API",
  "explanation_source": "ai | template"
}
```
`also_labels` is filled when two labels pick the same route (show it once).

## HTTP endpoints
- `GET /v1/health` -> `{ "status": "ok", "api_version": "1" }`
- `POST /v1/routes`
  body: `{ "from": {lat,lng}, "to": {lat,lng}, "depart_time": "ISO", "settings": { "max_extra_minutes": 10, "with_companion": false, "priorities": ["lighting"] } }`
  -> `{ "api_version", "scoring_version", "data_fetched_at", "routes": [Route result], "warnings": ["string"] }`
- Errors: `{ "error": { "code": "NO_ROUTE | UPSTREAM_TIMEOUT | BAD_REQUEST | UPSTREAM_ERROR | NOT_CONFIGURED", "message": "string" } }`
  HTTP: BAD_REQUEST 400, NO_ROUTE 404, UPSTREAM_ERROR 502, NOT_CONFIGURED 503, UPSTREAM_TIMEOUT 504 (UPSTREAM_ERROR, NOT_CONFIGURED added 24 Oct). Messages never echo the request or any key.
  Partial upstream failure returns 200 with `warnings`.
- Trips longer than about 5 km return BAD_REQUEST (demo-area limit). `depart_time` must include a time zone.
- (add more here)

## Watch relay endpoints (stretch; all in-memory, no accounts)
- `POST /v1/trips/pair` -> `{ "trip_id", "pair_code": "6 digits", "expires_in_s": 600 }` (called by the phone web app)
- `POST /v1/watch/pair` body `{ "pair_code", "device": "wearos" }` -> `{ "watch_token", "trip_id" }`
- `POST /v1/watch/heartbeat` (Bearer watch_token) body `{ "bpm": 0, "ts": "ISO", "source": "wearos | band | simulated" }` -> 204
- `GET /v1/trips/{trip_id}/stream` -> Server-Sent Events: `{ "type": "bpm | prompt | alert_sent | ack", ... }`
- `POST /v1/alerts` (Bearer watch_token or trip token) body `{ "trip_id", "location": {lat,lng}, "route_id" }` -> `{ "status": "sent | contact_not_opted_in | failed" }`
- `POST /v1/alerts/ack` body `{ "trip_id", "ok": true }`
- Rules: `source: "simulated"` must be shown as Simulated in every UI. Tokens expire at trip end. No bpm or coordinates stored or logged.

## Platform support matrix (what the web app must handle)
Android Chrome and iOS Safari 16.4+ (installed to home screen) are both required for the core demo. Web Bluetooth, vibration, and background tracking are NOT available on iOS; features must detect support and show a fallback message.

## Data source interface (server/data/)
- `get_places(area, time)` -> list of places with opening hours, `is_24h`, `category`, `source`, `fetched_at`.
  Implementations: `brightdata` (core), `apify` (supporting only), later `osm` / `overture`.
- Same pattern for roads (OSM), lighting (SF 311), transit (511/GTFS), incidents (SF open data), routing (Mapbox).
- Cache key: `(provider, area_cell, hour_bucket)`.

## Config and env
- Score weights: `scoring/scoring_v1.json` (weights must sum to 1.0)
- Env vars (names only, see `.env.example`): BRIGHTDATA_API_KEY, APIFY_TOKEN,
  MAPBOX_TOKEN (server), NEXT_PUBLIC_MAPBOX_TOKEN (browser, URL-restricted),
  ANTHROPIC_API_KEY, NEXT_PUBLIC_API_BASE_URL
