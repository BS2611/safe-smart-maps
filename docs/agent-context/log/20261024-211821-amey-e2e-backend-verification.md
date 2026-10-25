# e2e-backend-verification

- When: 2026-10-24 21:18
- Who: Amey (agent: claude-code)
- Branch / commit: amey/backend / committed together with this log (not pushed)
- Files touched: server/services/explain.py, tests/test_explain_wording_ttl.py, this log, STATE.md (Amey section)
- What changed: Two fixes so Claude explanations actually work: (1) `ANTHROPIC_MODEL=` (empty, copied from .env.example) made the model "" -> HTTP 400 on every call, now `or DEFAULT_MODEL`; (2) Haiku 5.5 thinks by default and used the 220-token cap on a thinking block (no text) -> request now sends `thinking: {"type":"disabled"}`. 3 regression tests added.
- Why: Without these the planner always used the template text; the Claude API is a sponsor integration.
- Decisions made in chat (also added to DECISIONS.md? yes/no): none. Server was started with PREFETCH_ON_STARTUP=0 for the test only, so no paid Bright Data refresh could start on the stale cache.

## Scenario (real, no mocks)
- POST /v1/routes, Palace of Fine Arts (37.8029,-122.4484) -> Montgomery BART (37.7894,-122.4013), priorities ["lighting"], max_extra_minutes 10.
- Request A: depart 2026-10-24T20:00-07:00. Request B: same trip 2026-10-25T02:00-07:00. Request C (after fix): same as A.
- Single uvicorn worker, run through a scratchpad launcher that only logged host/status/elapsed of outgoing httpx calls (no URLs, no headers).

## Services
- Live: Mapbox (3 requests per trip: 1 with alternatives + 2 detours; 2 routes remained after dedupe), Anthropic (1 call per displayed route, sequential).
- Cache: Bright Data places, 18 listings, STALE (about 1 h old, TTL 900 s) and served with a warning. Zero Bright Data requests in all three runs.
- OSM / Overpass: FAILED every time (overpass-api.de: connection refused from this network; kumi.systems timeout; private.coffee and mail.ru no answer). Planner degraded as designed: 200 with a warning, lighting / main_road / help_points = not sure.

## Results
- A (8 PM): 200, 1.9 s. safest mapbox-1 6050 m / 72.2 min / score 1.4 / 121 segs / 3 open places; balanced+fastest mapbox-0 5533 m / 66.4 min / score 0.0 / 111 segs / 0 open places. Explanation: template (before fix).
- B (2 AM): 200, 1.5 s. safest score 0.4, 1 open place (was 3); fastest unchanged at 0. Same cache, no Bright Data call. Time-of-day check PASS.
- C (after fix, same as A): 200, 4.6 s (Mapbox ~0.5 s, Anthropic ~3.4 s sequential). explanation_source "ai" on both routes.
- data_fetched_at 2026-10-25T03:15:59Z (cache time). Continuity ran on every candidate; every segment confidence "unknown".
- Contract: PASS on api_version, scoring_version, route fields, segment fields, geometry [lng,lat], continuity, warnings, data_fetched_at, error schema (400 for bad lat and for same-place trips).
- Default suite: 442 passed, 3 live deselected. `.env` and `.cache` ignored.

## Limitations / demo blockers
1. BLOCKER: Overpass unreachable from this network, so lighting, road type and help points are all "not sure" and scores rest on open_places alone (bands mostly red). Needs a reachable Overpass (set OVERPASS_URL to a working mirror, try another network/hotspot) and PREWARM_DEMO=1 so the 20-40 s OSM call is not paid in front of judges. Latency with a live Overpass cold start is untested (likely RISKY/BLOCKING on the first request).
2. Misleading wording: continuity `coverage_pct` is computed over known length only, so a route with 93-98% unknown shows coverage 100% and the template/Claude text says "100% stays near an open place" / "covered by lighting and activity data". The `notes` field does say "coverage not sure for 93%". Suggest: when coverage_known_pct is low, send coverage_pct=None (or the known share) to the explainer. Design call for Amey; not changed.
3. Segments with only one known factor score 0 and get band "red" with confidence "unknown". UI should paint by confidence, or planner should send band "unknown" below a minimum known weight. Not changed.
4. Cached places cover only the Palace bbox; most of this 5.5 km trip is outside it (warning shown). Demo trip should stay inside cached areas or prefetch a bigger area (needs approval: paid).
5. Cache is stale (TTL 900 s). Serving stale is by design; refresh only with approval.

- Unfinished / uncommitted: none after commit.
- Open issues / risks: items 1-5 above.
- Next step for whoever continues: find a reachable Overpass (`OVERPASS_URL=<mirror>`), rerun `.venv/bin/python -m pytest -m live` for the OSM test, then start with `PREWARM_DEMO=1` and re-run one POST /v1/routes to see real lighting data; then decide items 2 and 3.
- Needs from teammate: Bhavpreet: nothing for the backend; the UI should handle band "red" + confidence "unknown" until item 3 is decided.
