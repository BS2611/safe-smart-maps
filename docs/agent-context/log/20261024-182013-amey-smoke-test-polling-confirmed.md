# smoke-test-polling-confirmed

- When: 2026-10-24 (evening PT)
- Who: Amey (agent: claude-code)
- Branch / commit: amey/backend / see git log
- Files touched: server/data/brightdata.py (timeout_s default 90 -> 180), docs/agent-context/STATE.md (Amey section), this log
- What changed: Corrects the "Unfinished" note in 20261024-181314-amey-brightdata-live-verification. Ran `.venv/bin/python -m scripts.brightdata_smoke` (repo provider, no scratch code).
- Why: confirm the repo's own 202 -> poll -> download path against the real API.
- Decisions made in chat: none
- Contracts affected: none
- How it was tested (LIVE): run 1 FAILED after 3:07 with "Bright Data request failed: ReadTimeout" (initial POST exceeded the 90 s timeout; the sync call can hold longer than the 60 s seen earlier). Raised default timeout_s to 180. Run 2 (after 148 unit tests OK) succeeded in 2:49: "places returned: 19", 8 shown with category, raw category, open/closed/unknown and fetched_at. Mix of open, closed and unknown seen. Each run may have started a paid job (run 1 probably did).
- Unfinished / uncommitted: none
- Open issues / risks: a live fetch takes ~3 min, so prefetch/cache is required; no unit test pins the 180 s default.
- Next step for whoever continues: cache + prefetch layer around BrightDataPlacesProvider (CACHE_TTL_SECONDS), then OSM/Mapbox.
- Needs from teammate: none
