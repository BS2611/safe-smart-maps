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
  "known_weight_fraction": 0.7,
  "confidence": "high | low | unknown"
}
```
`confidence` (added with POST /v1/routes, additive) is derived from `known_weight_fraction` with `scoring_v1.json` `confidence`: >= 0.8 high, >= 0.5 low, else unknown. `unknown` must render as "not sure".
Factor names are exactly the keys of `scoring_v1.json` `weights` (`activity`, NOT `activity_estimate`; renamed 2026-10-24). A factor value is 0-100 or `null` = unknown, shown as "not sure". `score` is `null` and `band` is `unknown` when no factor is known. `known_weight_fraction` = share of total weight backed by known factors (a simple signal for how much the score rests on; no `confidence` label is defined yet). Bands are display labels, not a claim a route is safe or unsafe.

### Segment scoring (server/services/segmenter.py, segment_scoring.py) - hackathon-v1 heuristics
Not measurements of safety; tunable constants all live in `scoring/scoring_v1.json`.
- Segmenter input: ordered `(lat, lng)` route points; any point outside lat -90..90 / lng -180..180 raises `ValueError` (order is never guessed or swapped) (flat list; `join_legs` flattens legs). Repeats dropped; < 2 distinct points -> no segments. Length by haversine; `n = max(1, round(L / segment_length_m))` equal pieces. `Segment`: `index, segment_id, start, end, midpoint (halfway along path), length_m, coordinates, offset_m`.
- Arrival at a segment = `depart_at + offset_m / walking_speed_mps` (1.4 m/s) until the routing provider supplies timing.
- `score = sum(w_i * f_i over known) / sum(w_i over known)`; weights can be overridden per user and are renormalized.
- `open_places`: places OPEN at arrival within `radii_m.open_place` of the segment path -> `open_places_by_count[min(n, 3)]` = 0/50/75/100. Place data unavailable (`None`) -> unknown; available with zero open -> 0; unknown-hours places never count as open or closed, kept as evidence.
- `lighting` / `main_road`: nearest `RoadContext` within `radii_m.road_match` (25 m) of the midpoint. Road class trunk/primary/secondary/tertiary=100, residential=60, service=40, pedestrian=40; motorway/other/unknown/no match = unknown. Lighting is the bullet below.
- `help_points`: nearest police/hospital/fire_station to the segment, `max(0, 100*(1 - d/150))`. AreaContext unavailable -> unknown; available but empty -> 0 ("none found in queried area").
- `transit`: nearest stop with a GTFS departure in the next 15 minutes at the segment arrival (`GTFS_DIR`). No feed, or a feed that fails to load, stays null ("not sure"). A stop with no trip in the window scores 0.
- `activity`: estimate from OSM shop/busy-amenity density near the segment, multiplied down in the evening and after midnight. Not a count of people. Null when that OSM query did not run.
- `incidents`: SF open-data reports within 80 m. No dataset stays null. Zero reports scores 100, which means "no reports in the extract", not a safety claim. Weight stays 0.05 because the record reflects policing as much as events.
- `turns`: bearing change along the route. A turn is darker only when the matched road is tagged unlit. Unknown lighting is not a dark turn. `tunnel=yes` lowers the score. Always known from the route shape.
- `lighting`: OSM `lit` yes=100, no=0, missing or anything else stays null unless a mapped street lamp or an open 311 streetlight outage is nearby. Unknown is never scored as unlit.
- Scorer inputs: `SegmentScorer(config, places: list[Place] | None, area_context: AreaContext | None, weights=None)`; `None` = dataset unavailable, empty = available but nothing found. Scoring reads only; it never fetches.
- Segment score also carries `covered` (internal, not in `to_dict()`): True if an OPEN place (at arrival), a help point, or (when a GTFS feed is loaded) an active transit stop is within `radii_m.coverage` (75 m) of the segment; False only when places and area data are both available and nothing could count (no unknown-hours place nearby either); None = not sure. A missing transit feed does not mark a segment uncovered.
- Continuity (server/services/continuity.py, `compute_continuity(config, list[SegmentScore]) -> ContinuityResult`, `.to_dict()` gives the Route result's `route_score` + `continuity`): `average_score` = length-weighted mean of known scores; `worst_window_score` = lowest length-weighted mean over any `window_m` (200 m) stretch (whole route if shorter), with `worst_window_start_m/end_m`; `coverage_pct` = covered length / length with known coverage; `longest_gap_m` = longest consecutive run of segments with `covered == False`, in meters (unknown breaks a run, never extends one), `longest_gap_note` = "from X m to Y m along the route"; `gap_penalty` = max(0, gap - gap_limit_m) * gap_penalty_per_m, `gap_penalty_applied` = min(penalty, base); `route_score` = clamp(avg_weight*average + worst_window_weight*worst - applied, 0, 100). `route_score` is `null` (and `continuity.insufficient_data` true) when no segment has a score. Extra `continuity` keys: `average_score, gap_penalty, gap_penalty_applied, meets_coverage_target, route_length_m, unknown_length_m, insufficient_data, notes`. Unknown share is reported in `notes`/`unknown_length_m`, never scored as 0.
- Routing provider (Mapbox, other developer) must supply: ordered walking-route `(lat, lng)` points (legs concatenated), total duration/distance, and ideally per-leg timing. Feed `segment_route(points, cfg["segment_length_m"])`. Now provided by `RouteCandidate.as_lat_lng()`, `distance_m`, `duration_s` (see Routing provider below; no per-leg timing, steps are off).

### Routing provider (server/data/mapbox.py) - Mapbox walking candidates
Candidate generation only: no scoring, ranking or labels. Mapbox JSON is read only in this file.
```python
RouteCandidate(id: str, provider: str, coordinates: list[(lng, lat)], distance_m: float, duration_s: float)
MapboxWalkingProvider(token=None, timeout_s=12.0, client=None).get_walking_routes(origin, dest, waypoints=()) -> list[RouteCandidate]
```
- **Coordinate order is (longitude, latitude)** in `coordinates`, `origin` and `dest` (GeoJSON/Mapbox order). The segmenter and `geo.py` use (lat, lng): call `route.as_lat_lng()` to get that order; never swap by hand. A latitude outside +-90 is rejected, so an accidental swap fails loudly.
- `id` = `"mapbox-<n>"`, n = position in Mapbox's answer (0 = Mapbox's preferred route). A dropped bad route leaves a gap; ids never shift. `provider` is always `"mapbox"`.
- `distance_m` meters and `duration_s` seconds, exactly as Mapbox sends them (no conversion). Mapbox's walking time is its own estimate; segment arrival times still use 1.4 m/s unless changed.
- Request: Directions v5 `walking` profile, `alternatives=true`, `geometries=geojson`, `overview=full`, `steps=false`. Mapbox often returns only ONE walking route even with alternatives on (seen live), so do not assume 2-3 candidates. `waypoints` (optional `(lng, lat)` via points) forces one route through them (alternatives are off then); `services/candidates.py` uses it to build detours.
- Errors: `MapboxError` (a `RuntimeError`) with `kind`: `not_configured` (no `MAPBOX_TOKEN`, no request made), `timeout`, `failed` (HTTP error, bad JSON, no usable geometry), `empty` (Mapbox found no route). Invalid `origin`/`dest` raise `ValueError`. Messages never contain the token, URL or coordinates.
- A route with missing/short/non-numeric geometry or a non-positive distance/duration is dropped; unknown Mapbox fields are ignored.
- Feeding the segmenter: `segment_route(route.as_lat_lng(), cfg["segment_length_m"])`.

### Route planner (server/services/planner.py) - POST /v1/routes
Wires existing modules; it adds no scoring rules.
1. Candidates: `generate_candidates` (services/candidates.py) = Mapbox's own routes, then two detours forced through a via point left and right of the middle of the trip, near-duplicates removed (`scoring_v1.json` `candidates`). Ids are renumbered `mapbox-0..n` across the merged list. A failing detour is skipped; a failing main request fails the request.
2. Data: saved business listings are READ from the places cache (`places_lookup.py`; never fetches; no listing near the route -> `null` / "not sure" plus a warning; stale listings are used with their real date and a warning). OSM `AreaContext` comes from `OverpassContextProvider`, cached in memory per 0.01-degree area for 24 h (`data/ttl_cache.py`); failure -> lighting/road/help points "not sure" plus a warning.
3. Score: `segment_route(route.as_lat_lng(), segment_length_m)` -> `SegmentScorer(...).score_route(...)`. User `settings.priorities` boost up to two factors by `priorities.boost`, renormalized.
4. Continuity: Amey's `compute_continuity(cfg, scored)` (services/continuity.py), unchanged; the planner copies its `continuity` dict (coverage, longest gap and where it is, worst window, notes) into each route. Segment `covered` comes from his `SegmentScorer`.
5. Selection (`selector.py`): Fastest, Safest (best score within `max_extra_minutes`) and Balanced (`balanced_points_per_extra_min`); a route winning two labels is returned once with `also_labels`. A route with no score can only be Fastest. The API label is `safest`; the UI must say "better lit and more active" (never "safe").
6. Explanation (`explain.py`): Claude when `ANTHROPIC_API_KEY` is set, a fixed template otherwise or when the text breaks the wording rules (`wording.py`); `explanation_source` = `ai | template`.
Known limits: `via` is always `[]` (the Mapbox provider asks for `steps=false`, so there are no street names; `longest_gap_note` is Amey's "from X m to Y m along the route"); `segment_id` is `seg-<n>`; `open_places_count` counts distinct places open within 50 m of any segment at that segment's arrival time.
`SfDataError`-based providers in `data/sf_open_data.py` (311 streetlight outages, incidents) are wired through the planner and cached per area. A failure leaves that factor "not sure" and adds a warning. Transit is `GTFS_DIR` (`server/data/gtfs.py`); with no folder, transit stays "not sure".

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
- Errors: `{ "error": { "code": "NO_ROUTE | UPSTREAM_TIMEOUT | UPSTREAM_ERROR | NOT_CONFIGURED | BAD_REQUEST", "message": "string" } }`
  HTTP status: BAD_REQUEST 400, NO_ROUTE 404, UPSTREAM_ERROR 502, NOT_CONFIGURED 503, UPSTREAM_TIMEOUT 504. Validation errors list field names only, never the submitted values.
  Partial upstream failure returns 200 with `warnings`.
- `GET /v1/cache/status` -> `{ api_version, provider, ttl_seconds, areas: [{ area, status: fresh|stale|miss, refreshing, places, data_fetched_at, age_seconds, last_error }] }`
- (add more here)

## Data source interface (server/data/)
- `get_places(area, time)` -> list of places with opening hours, `is_24h`, `category`, `source`, `fetched_at`.
  Implementations: `brightdata` (core), `apify` (supporting only), later `osm` / `overture`.
- Same pattern for roads (OSM), lighting (SF 311), transit (511/GTFS), incidents (SF open data), routing (Mapbox).
- `ContextProvider.get_area_context(area: BoundingBox) -> AreaContext` (server/data/context.py; implementation `OverpassContextProvider` in server/data/osm.py, source "osm"). `AreaContext` = `roads`, `help_points`, `fetched_at`, plus `street_lamps`, `activity_points`, and `activity_known` (true only after a query that asked for shops and busy amenities). `RoadContext`: `coordinates` ((lat,lng) points), `road_class` (motorway|trunk|primary|secondary|tertiary|residential|service|pedestrian|other|unknown), `lit` (yes|no|unknown; missing tag = unknown, never no), `tunnel` (true only for an explicit `tunnel=yes` or `tunnel=building_passage`), `osm_id`, `name`, `raw_highway`, `source`, `fetched_at`. `HelpPoint`: `type` (police|hospital|fire_station), `lat`, `lng`, `name`, `osm_id`, `source`, `fetched_at`. OSM is cached in memory for 24 h. Raises `OsmError` on upstream failure. Scoring must treat `unknown` as "not sure". The segment JSON shape is unchanged: each factor is still 0-100 or null, with the same names.
- Cache key: `(provider, area)`; `area` = the BoundingBox that was fetched (a request inside a cached box reuses it). No `hour_bucket`: listings are not hour-specific, open/closed is computed per request from cached hours. File cache in `CACHE_DIR` (default `.cache/places`, git-ignored). Route requests only READ the cache (never fetch); stale entries are served with their original `fetched_at` while a background refresh runs; a miss returns no places ("not sure").

## Config and env
- Score weights: `scoring/scoring_v1.json` (weights must sum to 1.0)
- Env vars (names only, see `.env.example`): BRIGHTDATA_API_KEY, APIFY_TOKEN,
  MAPBOX_TOKEN (server), NEXT_PUBLIC_MAPBOX_TOKEN (browser, URL-restricted),
  ANTHROPIC_API_KEY, NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_MAPILLARY_TOKEN (browser, Mapillary client token for street-level photos; empty means the screen says street view is unavailable),
  NEXT_PUBLIC_GOOGLE_MAPS_API_KEY (optional browser key; if set, street view uses Google Street View instead of Mapillary),
  CACHE_TTL_SECONDS (default 86400), CACHE_DIR (default .cache/places),
  OVERPASS_URL (optional, default public overpass-api.de),
  GTFS_DIR (optional folder or .zip of a public GTFS feed, SF Muni or BART; empty means transit stays not sure),
  GTFS_DIR_EXTRA (optional second feed, same rules; no key),
  PREFETCH_ON_STARTUP (1 = background-refresh missing/stale demo areas at server start; needs BRIGHTDATA_API_KEY),
  WEB_ORIGINS (comma-separated browser origins allowed by CORS, default http://localhost:3000, never `*`),
  PREWARM_DEMO (1 = run the demo trip once at startup to warm the OSM cache; uses a few Mapbox calls),
  ANTHROPIC_MODEL (optional, default claude-haiku-5-5)
