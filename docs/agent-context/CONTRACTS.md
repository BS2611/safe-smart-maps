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
  "segment_id": "seg-0",
  "start": [lng, lat],
  "end": [lng, lat],
  "length_m": 48.3,
  "arrival_time": "2026-10-24T23:10:00-07:00",
  "score": 56.5,
  "band": "green | yellow | red | unknown",
  "factors": { "open_places": 0, "lighting": 100, "main_road": 100,
               "help_points": 45.3, "transit": null, "activity": null,
               "incidents": null, "turns": null },
  "unknown_factors": ["transit", "activity", "incidents", "turns"],
  "reasons": ["2 open places within 50 m", "lit road"],
  "data_fetched_at": "ISO time (oldest source used) or null",
  "known_weight_fraction": 0.7
}
```
Factor names are exactly the keys of `scoring_v1.json` `weights` (`activity`, NOT `activity_estimate`; renamed 2026-10-24). A factor value is 0-100 or `null` = unknown, shown as "not sure". `score` is `null` and `band` is `unknown` when no factor is known. `known_weight_fraction` = share of total weight backed by known factors (a simple signal for how much the score rests on; no `confidence` label is defined yet). Bands are display labels, not a claim a route is safe or unsafe.

### Segment scoring (server/services/segmenter.py, segment_scoring.py) - hackathon-v1 heuristics
Not measurements of safety; tunable constants all live in `scoring/scoring_v1.json`.
- Segmenter input: ordered `(lat, lng)` route points (flat list; `join_legs` flattens legs). Repeats dropped; < 2 distinct points -> no segments. Length by haversine; `n = max(1, round(L / segment_length_m))` equal pieces. `Segment`: `index, segment_id, start, end, midpoint (halfway along path), length_m, coordinates, offset_m`.
- Arrival at a segment = `depart_at + offset_m / walking_speed_mps` (1.4 m/s) until the routing provider supplies timing.
- `score = sum(w_i * f_i over known) / sum(w_i over known)`; weights can be overridden per user and are renormalized.
- `open_places`: places OPEN at arrival within `radii_m.open_place` of the segment path -> `open_places_by_count[min(n, 3)]` = 0/50/75/100. Place data unavailable (`None`) -> unknown; available with zero open -> 0; unknown-hours places never count as open or closed, kept as evidence.
- `lighting` / `main_road`: nearest `RoadContext` within `radii_m.road_match` (25 m) of the midpoint. lit yes=100, no=0, unknown=unknown. Class trunk/primary/secondary/tertiary=100, residential=60, service=40, pedestrian=40; motorway/other/unknown/no match = unknown.
- `help_points`: nearest police/hospital/fire_station to the segment, `max(0, 100*(1 - d/150))`. AreaContext unavailable -> unknown; available but empty -> 0 ("none found in queried area").
- `transit`, `incidents`, `activity`, `turns`: always unknown for now (no providers).
- Scorer inputs: `SegmentScorer(config, places: list[Place] | None, area_context: AreaContext | None, weights=None)`; `None` = dataset unavailable, empty = available but nothing found. Scoring reads only; it never fetches.
- Segment score also carries `covered` (internal, not in `to_dict()`): True if an OPEN place (at arrival) or a help point is within `radii_m.coverage` (75 m) of the segment; False only when places and area data are both available and nothing could count (no unknown-hours place nearby either); None = not sure. Transit is not counted yet.
- Continuity (server/services/continuity.py, `compute_continuity(config, list[SegmentScore]) -> ContinuityResult`, `.to_dict()` gives the Route result's `route_score` + `continuity`): `average_score` = length-weighted mean of known scores; `worst_window_score` = lowest length-weighted mean over any `window_m` (200 m) stretch (whole route if shorter), with `worst_window_start_m/end_m`; `coverage_pct` = covered length / length with known coverage; `longest_gap_m` = longest consecutive run of segments with `covered == False`, in meters (unknown breaks a run, never extends one), `longest_gap_note` = "from X m to Y m along the route"; `gap_penalty` = max(0, gap - gap_limit_m) * gap_penalty_per_m, `gap_penalty_applied` = min(penalty, base); `route_score` = clamp(avg_weight*average + worst_window_weight*worst - applied, 0, 100). `route_score` is `null` (and `continuity.insufficient_data` true) when no segment has a score. Extra `continuity` keys: `average_score, gap_penalty, gap_penalty_applied, meets_coverage_target, route_length_m, unknown_length_m, insufficient_data, notes`. Unknown share is reported in `notes`/`unknown_length_m`, never scored as 0.
- Routing provider (Mapbox, other developer) must supply: ordered walking-route `(lat, lng)` points (legs concatenated), total duration/distance, and ideally per-leg timing. Feed `segment_route(points, cfg["segment_length_m"])`.

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
- `ContextProvider.get_area_context(area: BoundingBox) -> AreaContext` (server/data/context.py; implementation `OverpassContextProvider` in server/data/osm.py, source "osm"). `AreaContext` = `roads: list[RoadContext]`, `help_points: list[HelpPoint]`, `fetched_at`. `RoadContext`: `coordinates` ((lat,lng) points), `road_class` (motorway|trunk|primary|secondary|tertiary|residential|service|pedestrian|other|unknown), `lit` (yes|no|unknown; missing tag = unknown, never no), `osm_id`, `name`, `raw_highway`, `source`, `fetched_at`. `HelpPoint`: `type` (police|hospital|fire_station), `lat`, `lng`, `name`, `osm_id`, `source`, `fetched_at`. Not cached yet. Raises `OsmError` on upstream failure. Scoring must treat `unknown` as "not sure".
- Cache key: `(provider, area)`; `area` = the BoundingBox that was fetched (a request inside a cached box reuses it). No `hour_bucket`: listings are not hour-specific, open/closed is computed per request from cached hours. File cache in `CACHE_DIR` (default `.cache/places`, git-ignored). Route requests only READ the cache (never fetch); stale entries are served with their original `fetched_at` while a background refresh runs; a miss returns no places ("not sure").

## Config and env
- Score weights: `scoring/scoring_v1.json` (weights must sum to 1.0)
- Env vars (names only, see `.env.example`): BRIGHTDATA_API_KEY, APIFY_TOKEN,
  MAPBOX_TOKEN (server), NEXT_PUBLIC_MAPBOX_TOKEN (browser, URL-restricted),
  ANTHROPIC_API_KEY, NEXT_PUBLIC_API_BASE_URL,
  CACHE_TTL_SECONDS (default 86400), CACHE_DIR (default .cache/places),
  OVERPASS_URL (optional, default public overpass-api.de),
  PREFETCH_ON_STARTUP (1 = background-refresh missing/stale demo areas at server start; needs BRIGHTDATA_API_KEY)
