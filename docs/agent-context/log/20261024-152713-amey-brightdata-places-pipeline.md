# brightdata-places-pipeline

- When: 2026-10-24 15:27
- Who: Amey (agent: claude-code)
- Branch / commit: amey/brightdata-places / see git log (one commit with this log)
- Files touched: server/data/models.py (new), server/data/opening_hours.py (new), server/data/brightdata.py (stub replaced), scripts/brightdata_smoke.py (new), scripts/__init__.py, tests/__init__.py, tests/test_places.py (new), .env.example (name BRIGHTDATA_PLACES_DATASET_ID added, no value), this log, STATE.md (Amey section)
- What changed: Place + BoundingBox models. Bright Data provider using Web Scraper API "Google Maps places, discover by location" (POST api.brightdata.com/datasets/v3/scrape, dataset gd_m8ebnr0q2qlklc02fz, Bearer key from BRIGHTDATA_API_KEY). Raw records are converted to Place only inside brightdata.py. Opening-hours parser + evaluate_open_status(place, arrival) -> open/closed/unknown in opening_hours.py (pure, no network).
- Why: M2.2 (live places) and M2.3 (open at arrival time).
- Decisions made in chat (also added to DECISIONS.md? no): area = BoundingBox (internal, not in CONTRACTS); place timezone assumed America/Los_Angeles; missing/unreadable hours = unknown; is_24h only if all 7 days say open 24 hours; unittest used instead of pytest to avoid a new dependency. DECISIONS.md/CONTRACTS.md are shared and not edited; proposals below.
- Contracts affected: none edited. get_places now returns list[Place] (dataclass) instead of list[dict]; CONTRACTS only says "list of places", so no conflict, but the Place shape should be added to CONTRACTS (needs Amey/Bhav approval).
- How it was tested: `.venv/bin/python -m unittest discover -s tests -t .` -> 16 tests OK (hours inside/outside day, close exclusive, missing=unknown, unreadable day, explicit Closed, 24h, past-midnight spill, split hours, timezone conversion, naive datetime rejected, category word boundaries, partial records, JSON array/NDJSON body). Fixtures are hand-written and labeled in the test file.
- LIVE CALL: NOT DONE. No BRIGHTDATA_API_KEY in env, repo or ~/.env. `.venv/bin/python -m scripts.brightdata_smoke` ran and printed "FAILED: BRIGHTDATA_API_KEY is not set". The network path in BrightDataPlacesProvider.get_places is therefore untested.
- Unfinished / uncommitted: live call; confirming the real open_hours shape; nothing uncommitted after commit.
- Open issues / risks:
  - The Bright Data docs do not show the open_hours format. The parser assumes {"Monday": "9AM-5PM"} or a list of {day, hours}. If the real shape differs, hours come back as unknown (safe) and parse_weekly_hours needs an update.
  - Sync /scrape may return 202 or time out for location discovery; if so switch to /trigger + snapshot polling (TECHNICAL_SPEC wants ~8 s timeout and a cache fallback; not built).
  - No cache yet (cache key is in CONTRACTS).
  - Proposed DECISIONS lines: "Bright Data via Web Scraper API Google Maps dataset"; "place timezone America/Los_Angeles".
- Next step for whoever continues: add BRIGHTDATA_API_KEY=<key> to .env (git-ignored), then run `.venv/bin/python -m scripts.brightdata_smoke`. Expect a place count, names, categories, open/closed/unknown, fetched_at. Then check one raw record's open_hours shape and adjust opening_hours.parse_weekly_hours if statuses are all unknown.
- Needs from teammate: approval to add the Place model and BoundingBox `area` to CONTRACTS.md; same 9 items as the earlier log still open.
