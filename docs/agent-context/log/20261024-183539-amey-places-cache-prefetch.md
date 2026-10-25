# places-cache-prefetch

- When: 2026-10-24 19:00 PT
- Who: Amey (agent: claude-code)
- Branch / commit: amey/backend / see git log (one commit with this log)
- Files touched: server/data/cache.py (new), server/services/prefetch.py (new), server/api/cache.py (new), server/main.py (provider + startup prefetch + cache router + load_dotenv), scripts/prefetch_places.py (new), tests/test_cache.py (new), tests/__init__.py (sets PREFETCH_ON_STARTUP=0 so tests never start a paid job), .env.example (names: CACHE_DIR, PREFETCH_ON_STARTUP; CACHE_TTL_SECONDS 900 -> 86400), .gitignore (.cache/), CONTRACTS.md, DECISIONS.md, STATE.md (Amey section), this log
- What changed: File cache around any PlacesProvider (CachedPlacesProvider + FilePlacesCache, one atomic JSON file per area). get_places only READS the cache (empty list on a miss = "not sure"); it never calls Bright Data. Stale entries are served with their original fetched_at while a single-flight background thread refreshes. Failed refresh keeps the old entry and records last_error (no secrets). An empty upstream result never replaces a non-empty entry. Server start runs a background prefetch for the Palace of Fine Arts area only if the entry is missing/stale, PREFETCH_ON_STARTUP is not 0, and BRIGHTDATA_API_KEY is set (existence check only). Manual: `.venv/bin/python -m scripts.prefetch_places [--force]`. New GET /v1/cache/status.
- Why: a live fetch takes ~3 min and costs credit; route requests must never wait on it.
- Decisions made in chat (also added to DECISIONS.md? yes): key is (provider, area) with no hour_bucket (open/closed is computed per request from cached hours); serve stale + refresh in background; JSON files in .cache/ plus startup prefetch; TTL default 24h.
- Contracts affected: CONTRACTS.md "Data source interface" cache key (hour_bucket removed, area is the fetched BoundingBox), new endpoint GET /v1/cache/status, env CACHE_TTL_SECONDS/CACHE_DIR/PREFETCH_ON_STARTUP.
- How it was tested: `.venv/bin/python -m unittest discover -s tests -t .` -> Ran 162 tests, OK (148 old + 14 new in test_cache.py: JSON round trip, miss never calls upstream, fresh/stale, survives restart, covering-area reuse, corrupt file, failed refresh keeps old, empty result guard, single-flight background refresh, no temp files, prefetch only when missing/stale, status shape, endpoint). Ran uvicorn with PREFETCH_ON_STARTUP=0: GET /v1/cache/status -> status "miss", places 0; GET /v1/health -> 200. The cache tests use a labeled FAKE upstream. NOT RUN: a real prefetch (no paid Bright Data job was started this session), so file cache + real provider together are untested live.
- Unfinished / uncommitted: nothing after commit. Not pushed.
- Open issues / risks:
  - The local .env has CACHE_TTL_SECONDS=900 (copied from the old .env.example); status showed ttl_seconds 900. .env was not touched. Edit it to 86400 or delete the line (default is 86400).
  - Cache lookup of a box not covered by a cached box is a miss (no places). Route corridors outside the Palace box get no places until prefetched; DEMO_AREAS in server/services/prefetch.py is the list to extend.
  - With multiple uvicorn workers each would start its own prefetch (single-flight is per process). Run one worker for the demo.
  - Cache files hold public place data only; .cache/ is git-ignored.
  - The 8 behavior questions in log 20261024-174045 are still undecided.
- Next step for whoever continues: run `.venv/bin/python -m scripts.prefetch_places` once (about 3 min, one paid job), then `curl localhost:8000/v1/cache/status` after starting the server: expect status "fresh", places ~19. Then OSM/Mapbox segment data.
- Needs from teammate: Bhavpreet: note the new GET /v1/cache/status and that places can be "not sure" on a miss; approval to add Place/BoundingBox to CONTRACTS.md still open.
