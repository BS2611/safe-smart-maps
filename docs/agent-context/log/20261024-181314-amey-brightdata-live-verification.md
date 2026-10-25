# brightdata-live-verification

- When: 2026-10-24 (evening PT)
- Who: Amey (agent: claude-code)
- Branch / commit: amey/backend / see git log (commit "Verify Bright Data live; fix lat/lon, blank dataset id, 202 polling, hour formats")
- Files touched: server/data/brightdata.py, server/data/opening_hours.py, tests/test_provider_failures.py, tests/test_brightdata_live_shape.py (new), tests/fixtures/brightdata_live_shape_sample.json (new, labeled), docs/agent-context/BRIGHTDATA.md (202 line), STATE.md (Amey section), this log
- What changed: Ran the REAL Bright Data Web Scraper API (Google Maps, discover_new by location, dataset gd_m8ebnr0q2qlklc02fz) for the Palace of Fine Arts. Found and fixed 4 mismatches:
  1. Blank `BRIGHTDATA_PLACES_DATASET_ID=` (as in .env.example) overrode the default -> HTTP 400 "dataset_id is not allowed to be empty". Blank now = unset.
  2. Sync call returned HTTP 202 + snapshot_id after ~60 s. Provider now polls /progress/<id> then downloads /snapshot/<id>?format=json (max_wait_s=300, poll 5 s). failed/timeout/401/403/404 raise BrightDataError.
  3. Real coordinate fields are `lat` / `lon`, not `latitude`/`longitude` (0 of 60 normalized before). `latitude`/`longitude` kept as fallback.
  4. Real open_hours is a dict {"Monday": "7 AM-3 PM"} using U+202F narrow no-break spaces (already handled by \s), plus formats the parser missed: shared meridiem ("5-10 PM", "12-8:30 PM"), dot minutes ("5.00 am"). Added; "11-2 PM" is read as 11 AM-2 PM.
- Why: AGENTS.md rule: never claim it works unless run; unit tests had assumed the shape.
- Decisions made in chat (also added to DECISIONS.md? yes/no): none new
- Contracts affected: none (Place model unchanged)
- How it was tested (LIVE): 1st request -> 400 (blank dataset id). 2nd request (the one paid job) -> 202 after 60.5 s; polled snapshot sd_mvn4okc5l5uhwxv0v -> status ready, records 60, errors 0, download HTTP 200, 552 KB. Real response fields used: name, place_id, category, lat, lon, open_hours (59/60 present). 0 duplicate place_ids. Replayed the saved real snapshot (no new request) through the fixed code: 60/60 normalized, 59/60 hours parsed (all 7 days), 0 unparsed day strings, 19 places inside the Palace box after dedupe; Sat 8 PM PT: 42 open, 17 closed, 1 unknown (the place with no hours). Categories: 23 restaurant, 15 cafe, 13 convenience_store, 2 gas_station, 1 bar, 6 other.
  Unit tests: `.venv/bin/python -m unittest discover -s tests` -> 148 tests OK (was 140). GET /v1/health -> 200 {"status":"ok","api_version":"1"}. .env still git-ignored, not staged.
- Unfinished / uncommitted: the fixed provider's own end-to-end path (POST -> 202 -> poll -> download) was exercised against the real API only via a scratch script that made the same calls; the repo provider's polling code is covered by faked-network tests, not by a second paid live run. Re-run `.venv/bin/python -m scripts.brightdata_smoke` (takes ~1-3 min) to confirm when convenient.
- Open issues / risks: a request takes 60+ s, so it must be prefetched/cached, never run on a user click (caching is the next milestone). API returns places beyond the requested box (60 raw, 19 inside); the area filter handles it. Time of an hours string like "8 AM-2 AM" relies on overnight handling (tested). Hours timezone is assumed SF.
- Next step for whoever continues: add the cache layer (CACHE_TTL_SECONDS) around BrightDataPlacesProvider with prefetch for the demo area, then OSM/Mapbox segment data.
- Needs from teammate: none
