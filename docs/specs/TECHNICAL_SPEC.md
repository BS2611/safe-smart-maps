# Safe Smart Maps – Technical Specification

Version 0.1 · Companion to FUNCTIONAL_SPEC.md

## 1. Stack
| Concern | Choice |
|---|---|
| Frontend | Next.js (TypeScript) responsive PWA for Android and iOS, Mapbox GL JS |
| Watch (stretch) | Kotlin Wear OS companion app (Samsung Galaxy Watch), Health Services heart rate |
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
  "weights": {"open_places":0.25,"lighting":0.20,"main_road":0.15,"help_points":0.10,
              "transit":0.10,"activity":0.10,"incidents":0.05,"turns":0.05},
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
- Location and heart-rate data processed in memory (watch, phone page, short-lived relay), not persisted after the trip; logs must not contain coordinates tied to a user.
- CORS restricted to the frontend origin.

## 8. Platforms, watch and heartbeat alert (stretch)
### 8.1 Platform strategy (decision: one responsive web app + optional Wear OS companion)
- `web/` is a Next.js **PWA** (manifest, service worker, installable). Runs in Android Chrome and iOS Safari; no separate native phone apps.
- Browser limits we design around: no Web Bluetooth on iOS; no background geolocation or timers when the page is hidden or the phone is locked (use the Screen Wake Lock API while walking, iOS 16.4+); no vibration on iOS; web push on iOS only after "Add to Home Screen" (16.4+). Every feature checks support and shows a plain fallback message.
- Layout: mobile first (375 x 812 and 360 x 640), safe-area insets (`env(safe-area-inset-*)`), bottom sheets, 48 px targets, keyboard-aware inputs, desktop as a wider two-pane layout.
- Mapbox GL JS runs on both; cap map pixel ratio and segment count on low-end phones.

### 8.2 Samsung / Wear OS companion (`watch/`, stretch)
- Native Kotlin Wear OS app (Galaxy Watch 4 or newer runs Wear OS; confirm the owned model, see OPEN_QUESTIONS). Heart rate via Health Services (`androidx.health:health-services-client`, permission BODY_SENSORS). Verify exact API on the real watch early.
- Why a watch app instead of the phone browser: a web page cannot read a watch, and a locked phone suspends the page. The watch runs on its own and can call HTTPS over Wi-Fi/LTE or via the paired phone's connection.
- Pairing: phone web app calls `POST /v1/trips/pair` and shows a 6-digit code (valid 10 min); the watch app enters it and calls `POST /v1/watch/pair` to get a short-lived token tied to that trip only. No accounts.
- Data flow: watch -> `POST /v1/watch/heartbeat` (bpm, timestamp, source) -> backend relay (memory only) -> phone page via `GET /v1/trips/{id}/stream` (Server-Sent Events) for display.
- The **watch computes the baseline and trigger locally** (heart-rate spike plus a second sign such as sudden stop or very fast pace from watch motion sensors) so it works with the phone locked. On trigger it shows "Are you OK?" with haptics; no answer in ~30 s -> `POST /v1/alerts`.
- Backend sends the contact message (provider TBD, e.g. SMS service) with live location and route; contact must have opted in. Not built => demo shows the prompt flow and says so.
- Privacy: relay holds readings in memory with a short TTL, deletes everything at trip end, logs no bpm or coordinates tied to a person, token expires with the trip.
- Fallbacks in order: Wear OS app -> Bluetooth band (Android Chrome only) -> labeled simulated reading (`source: "simulated"`, shown in the UI as Simulated). Apple Watch is out of scope.

### 8.3 Watch UI constraints
Round ~1.2 in screen, glanceable: pairing code entry, walking status, prompt with big "I'm OK", alert-sent with cancel. One action per screen, high contrast, haptic pattern for the prompt. See `docs/design/STITCH_UI_BRIEF.pdf`.
## 9. Repository layout
```nCalHack_13/   (repo root)
  AGENTS.md CLAUDE.md README_FIRST.md .cursor/ .claude/ scripts/
  docs/agent-context/  STATE, CONTRACTS, DECISIONS, OPEN_QUESTIONS, log/
  docs/specs/          FUNCTIONAL_SPEC, TECHNICAL_SPEC, TASKS
  scoring/scoring_v1.json
  web/      Next.js PWA (presentation)
  watch/    Wear OS companion app (stretch)
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

