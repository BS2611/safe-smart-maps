# S1 + S2: scoring pipeline, routes API, and the web screens

- When: 2026-10-24 17:35 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: ui / see git log
- Files touched: server/services/* (geo, segmenter, scoring, continuity, selector, enrichment, planner, explain, reasons, wording, schemas), server/data/* (cache, errors, osm, sf_open_data, transit, mapbox), server/api/routes.py, server/wiring.py, server/main.py (EDITED, Amey's file: router, CORS, error shape, planner startup), scoring/scoring_v1.json (EXTENDED, shared: bands, confidence, selection, factor tuning), tests/* (new + fakes + fixtures), web/* (all screens, lib, tests, e2e), scripts/verify.sh, docs
- What changed: Backend: 50 m segmenter, 8-factor scoring with "not sure" handling, continuity rule, selector, enrichment from providers, planner with parallel provider calls and graceful failure, POST /v1/routes, Mapbox routing provider, OpenStreetMap (Overpass) and SF 311/incident providers, Claude explainer with template fallback and wording filter, TTL caches. Web: Welcome (+location-off), Plan trip, Preferences, Checking, Results (map or SVG fallback + 3 cards), Route detail, 8 PM vs 1 AM compare, How scores work.
- Decisions made in chat (also added to DECISIONS.md? yes): 5 lines added today 17:30.
- Contracts affected: CONTRACTS.md (route_id, via, error codes NOT_CONFIGURED/UPSTREAM_ERROR, null factors/score, 5 km limit). Amey must confirm.
- How it was tested (all run, all green): pytest 163 passed (96% coverage; scoring, continuity, selector, enrichment, explain, reasons, geo 100%); ruff clean; vitest 192 passed (98% lines); tsc and next lint clean; next build OK; Playwright 33 passed (11 tests x iPhone WebKit, Android Chromium, 360 px) against a production build; scripts/check-secrets.sh OK. LIVE: OpenStreetMap, SF 311 and SF incidents responded in `pytest -m live`. NOT RUN LIVE (no keys here): Mapbox routing, Bright Data places, Claude explanations, real Mapbox GL map rendering. Those paths are unit-tested with labeled fixtures only.
- Unfinished / uncommitted: nothing uncommitted after this commit. Not pushed.
- Open issues / risks:
  - No Mapbox, Bright Data or Anthropic keys in this environment: the live demo path is untested end to end. Add keys to .env, then run `pytest -m live` and the app.
  - Bright Data open_hours format is still an assumption (Amey's log): if every place is "unknown", fix parse_weekly_hours.
  - Overpass is slow (20-30 s); first request for a new area is slow, later ones are cached 24 h. Pre-warm planned in S4.
  - A browser run under heavy machine load once timed out 4 WebKit tests (31 min); alone they pass in 1 min. Workers limited to 3 locally, 2 in CI.
  - I edited Amey's server/main.py and scoring/scoring_v1.json (shared). Changes are additive; his tests still pass.
  - Figma items still open: product name, red asterisk button, missing screens in Figma (Plan, Results, Detail were designed from the brief).
- Next step for whoever continues: S3 items in docs/specs/TASKS.md (explanations are done; remaining: caching pre-warm, polish), then S4 hardening (a11y automation, PWA install, Android/iPhone real-device check).
- Needs from teammate: Amey: review CONTRACTS and my edits to main.py and scoring_v1.json; add tzdata to server/requirements.txt.
