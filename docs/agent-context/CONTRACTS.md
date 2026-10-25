# CONTRACTS - formats and interfaces both sides rely on

SOURCE OF TRUTH. `docs/specs/TECHNICAL_SPEC.md` must match this file; if they
disagree, this file wins and the spec gets fixed. If you change anything here,
update this file in the same commit and log it (field "Contracts affected").
Status: DRAFT v1 - Amey (backend) must confirm before server/ code is written.

## Folder layout (repo root = this folder)
- `web/`      Next.js frontend (Bhavpreet)
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
  "score": 0,
  "band": "green | yellow | red | unknown",
  "factors": { "open_places": 0, "lighting": 0, "main_road": 0,
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
  "also_labels": [],
  "duration_min": 0,
  "extra_min": 0,
  "distance_m": 0,
  "route_score": 0,
  "continuity": { "coverage_pct": 0, "longest_gap_m": 0,
                  "longest_gap_note": "near the park", "worst_window_score": 0 },
  "open_places_count": 0,
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
- Errors: `{ "error": { "code": "NO_ROUTE | UPSTREAM_TIMEOUT | BAD_REQUEST", "message": "string" } }`
  Partial upstream failure returns 200 with `warnings`.
- `GET /v1/cache/status` -> `{ api_version, provider, ttl_seconds, areas: [{ area, status: fresh|stale|miss, refreshing, places, data_fetched_at, age_seconds, last_error }] }`
- (add more here)

## Data source interface (server/data/)
- `get_places(area, time)` -> list of places with opening hours, `is_24h`, `category`, `source`, `fetched_at`.
  Implementations: `brightdata` (core), `apify` (supporting only), later `osm` / `overture`.
- Same pattern for roads (OSM), lighting (SF 311), transit (511/GTFS), incidents (SF open data), routing (Mapbox).
- Cache key: `(provider, area)`; `area` = the BoundingBox that was fetched (a request inside a cached box reuses it). No `hour_bucket`: listings are not hour-specific, open/closed is computed per request from cached hours. File cache in `CACHE_DIR` (default `.cache/places`, git-ignored). Route requests only READ the cache (never fetch); stale entries are served with their original `fetched_at` while a background refresh runs; a miss returns no places ("not sure").

## Config and env
- Score weights: `scoring/scoring_v1.json` (weights must sum to 1.0)
- Env vars (names only, see `.env.example`): BRIGHTDATA_API_KEY, APIFY_TOKEN,
  MAPBOX_TOKEN (server), NEXT_PUBLIC_MAPBOX_TOKEN (browser, URL-restricted),
  ANTHROPIC_API_KEY, NEXT_PUBLIC_API_BASE_URL,
  CACHE_TTL_SECONDS (default 86400), CACHE_DIR (default .cache/places),
  PREFETCH_ON_STARTUP (1 = background-refresh missing/stale demo areas at server start; needs BRIGHTDATA_API_KEY)
