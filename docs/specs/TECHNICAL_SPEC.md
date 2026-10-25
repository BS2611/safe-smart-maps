# Safe Smart Maps – Technical Specification

Version 0.1 · Companion to FUNCTIONAL_SPEC.md

## 1. Stack
| Concern | Choice |
|---|---|
| Frontend | Next.js (TypeScript), Mapbox GL JS |
| Backend | Python, FastAPI (Django is the alternative; decide at kickoff), pydantic models |
| Live data | Bright Data (core feed: business listings, opening hours) |
| Supporting data | OpenStreetMap (road/lit tags), SF 311 (streetlight outages), 511/GTFS (transit), SF open data (incidents). Apify for supporting sources/scheduled runs (see docs/agent-context/OPEN_QUESTIONS.md) |
| Routing / geocoding | Mapbox Directions (walking, alternatives), Mapbox Geocoding |
| Explanations | Claude API |
| Optional | Convex (state), Cartesia (voice) |

## 2. Three-layer architecture
```
Presentation  (Next.js)         UI, map, forms, cards. No scoring logic.
     │  HTTPS JSON  /v1/...
Service       (FastAPI)         Candidate generation, segment scoring,
                                continuity rule, route selection, explanations.
     │  interfaces only
Data-access   (FastAPI pkg)     Provider adapters + cache. No business rules.
     │
External: Bright Data, Mapbox, OSM, 311, 511, SF open data, Claude API
```
Rules: each layer only calls the layer directly below it; the service layer depends on **interfaces**, never on a specific provider.

### 2.1 Presentation layer
- Pages: trip planner (search, time picker, settings), results (map + cards), optional heartbeat screen.
- Mapbox GL JS GeoJSON line layer; per-segment color from `segments[].band` (green/yellow/red).
- Calls only the backend API; the Mapbox public token is URL-restricted and read from env.

### 2.2 Service layer (domain)
Modules:
- `candidates` – request 5–8 routes: Mapbox alternatives + detours via waypoints through high-scoring streets.
- `segmenter` – split each route into ~50 m segments with an estimated arrival time at each.
- `scoring` – segment score from weights in `scoring/scoring_v1.json`.
- `continuity` – coverage, longest gap, worst 200 m window, gap penalty.
- `selector` – picks Fastest, Safest (within extra-minutes cap), Balanced; merges duplicates.
- `explain` – builds a compact JSON of scores/reasons, calls Claude, returns plain-language summary; falls back to template text if the call fails.

### 2.3 Data-access layer
Interfaces (Python `Protocol`/ABC):
- `PlacesProvider.get_places(area, time) -> list[Place]`  (Bright Data implementation today)
- `RoadProvider.get_road_attributes(area)` (OSM)
- `LightingProvider.get_outages(area)` (SF 311)
- `TransitProvider.get_service(area, time)` (511/GTFS)
- `IncidentProvider.get_incidents(area)` (SF open data)
- `RoutingProvider.get_walking_routes(origin, dest, waypoints)` (Mapbox)
- `Cache` – key = `(provider, area_cell, hour_bucket)`, TTL configurable (default ~15 min for demo).

Place model includes `open_intervals`, `is_24h`, `category`, `source`, `fetched_at`. Opening-hours text is converted to open/closed at a given arrival time in this layer.

## 3. Scoring config (versioned)
`scoring/scoring_v1.json`:
```json
{
  "version": "scoring_v1",
  "weights": {"open_places":0.22,"lighting":0.22,"main_road":0.13,"help_points":0.10,
              "transit":0.12,"activity":0.08,"incidents":0.05,"turns":0.08},
  "segment_length_m": 50,
  "radii_m": {"open_place":50,"help_point":150,"coverage":75},
  "continuity": {"coverage_target":0.80,"gap_limit_m":150,"window_m":200,
                 "avg_weight":0.5,"worst_window_weight":0.5,"gap_penalty_per_m":0.1}
}
```
Weights must sum to 1.0 (validated at startup). User factor preferences adjust weights within bounds and are renormalized. `gap_penalty_per_m` is a starting value to tune.

## 4. API contract
The contract lives in `docs/agent-context/CONTRACTS.md` (source of truth: endpoints `/v1/health` and `/v1/routes`, Segment score, Route result, errors, versioning). Do not duplicate it here; if this spec and CONTRACTS.md disagree, CONTRACTS.md wins.

## 5. Scoring algorithm (pseudo)
```
for route in candidates:
  segs = segment(route, 50m); assign arrival_time(seg) = depart_at + cumulative_walk_time
  for seg in segs:
    factor scores (0-100) from providers at arrival_time
    seg.score = sum(weight_i * factor_i)
  avg = mean(seg.score)
  worst = min over rolling 200m of mean(seg.score)
  coverage = share of segs within 75m of open place / help point / active transit
  gap = longest run of uncovered segments (m)
  penalty = max(0, gap - 150) * gap_penalty_per_m
  route.score = 0.5*avg + 0.5*worst - penalty
select: fastest = min duration
        safest  = max score where extra_min <= cap
        balanced = max (score - lambda * extra_min)
```

## 6. Bright Data usage
- Live fetch of listings and opening hours for the demo corridor on each (uncached) request; results cached by area+hour with a visible `data_fetched_at`.
- Must handle: blocked pages (retry with backoff, then cache fallback, then "not sure"), slow responses (timeouts ~8 s with partial results), empty results (explicit warning).
- Public data only: no login/paywall scraping, no personal data. No mocked or hardcoded data in the demo path; test fixtures live only in tests.
- If Apify is used, it must not fetch the same data as Bright Data.

## 7. Security and privacy
- Secrets only in environment variables; `.env` git-ignored; `.env.example` committed with empty values. Repo scanned for keys before submission.
- Mapbox server token stays in backend; the browser token is URL-restricted.
- Location and heart-rate data processed in memory/on-device, not persisted after the trip; logs must not contain coordinates tied to a user.
- CORS restricted to the frontend origin.

## 8. Heartbeat alert (stretch)
Client-side only: Web Bluetooth (Chrome/Android) or labeled simulator → baseline over first minutes → trigger on spike + secondary sign → 30 s confirm → call `POST /v1/alerts` (sends contact message with live location). Contact opt-in required. Alert delivery provider TBD; if not built, the demo shows the prompt flow only and says so.

## 9. Repository layout
```nCalHack_13/   (repo root)
  AGENTS.md CLAUDE.md README_FIRST.md .cursor/ .claude/ scripts/
  docs/agent-context/  STATE, CONTRACTS, DECISIONS, OPEN_QUESTIONS, log/
  docs/specs/          FUNCTIONAL_SPEC, TECHNICAL_SPEC, TASKS
  scoring/scoring_v1.json
  web/      Next.js app (presentation)
  server/   api/ -> services/ -> data/ (providers, cache)
  tests/fixtures/  labeled fixtures only
  .env.example
```n
## 10. Testing
- Unit: scoring weights, continuity math (gap, window, coverage), opening-hours → open/closed at arrival time, selector merge logic.
- Integration: `/v1/routes` on the demo corridor at 8 PM and 1 AM; blocked/slow/empty provider simulations.
- Manual: demo script run-through, secrets scan.

## 11. Performance and deployment
Target < 10 s for an uncached demo-corridor request, < 2 s cached. Deploy frontend and backend to any simple host (e.g., Vercel + a small container host); fall back to running locally for the demo if needed.

## 12. Backward compatibility and scalability
Scoring weights in one versioned config; providers behind interfaces (swap Bright Data for OSM/Foursquare/Overture without touching scoring); routing behind an interface; cache scored segments by area+hour; `api_version` on every response.

