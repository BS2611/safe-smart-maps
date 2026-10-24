# backend-scaffold

- When: 2026-10-24 12:41 PT
- Who: Amey (agent: claude-code)
- Branch / commit: amey/backend-scaffold / see git log (one commit)
- Files touched: scoring/scoring_v1.json; server/main.py, server/requirements.txt, server/api/health.py, server/services/{health,scoring_config}.py, server/data/{places,brightdata}.py, empty __init__.py files; this log; STATE.md (Amey section)
- What changed: Added scoring_v1.json (copied from TECHNICAL_SPEC section 3; weights sum to 1.0). Added a FastAPI scaffold with layers api/ -> services/ -> data/. GET /v1/health returns {"status":"ok","api_version":"1"}. App refuses to start if weights do not sum to 1.0. Added abstract PlacesProvider.get_places(area, time) and an empty BrightDataPlacesProvider that raises NotImplementedError (no fake data).
- Why: Task from Amey: backend scaffold, steps 1-3 and 5; step 4 skipped (see below).
- Decisions made in chat (also added to DECISIONS.md? no): FastAPI chosen (answers OPEN_QUESTIONS #5 in practice). Not written to DECISIONS.md or OPEN_QUESTIONS.md because those are shared files and the task said touch only server/ and scoring/. Amey should add the line.
- Contracts affected: none edited.
- How it was tested: Created .venv, pip install -r server/requirements.txt, ran `uvicorn server.main:app --port 8000`, `curl -i localhost:8000/v1/health` returned 200 and {"status":"ok","api_version":"1"}. Changed "turns" to 0.10 temporarily: startup failed with "scoring_v1: weights sum to 1.05, expected 1.0"; restored the file. No unit tests written yet.
- Step 4 (Bright Data test call): SKIPPED. No key given, no .env in the repo, no BRIGHTDATA env var set.
- Unfinished / uncommitted: nothing after the commit. .venv/ is git-ignored.
- Open issues / risks: pull said "no tracking information" (main has no upstream); main and origin/bhav/initial-kit-and-specs are the same commit, so nothing was missed. STATE.md "Last full review by a human" is blank; Amey should confirm STATE is true. Run command was not added to a README (README is a shared file).
- Next step for whoever continues: Get a Bright Data key, put BRIGHTDATA_API_KEY in .env (never git), then implement BrightDataPlacesProvider.get_places in server/data/brightdata.py and make one real call for a business near Palace of Fine Arts, printing its opening hours. Run the server with:
  python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt && .venv/bin/uvicorn server.main:app --reload --port 8000
  then curl localhost:8000/v1/health.

## Needs from teammate (CONTRACTS.md review; file not edited)
1. Name mismatch: scoring weight key is `activity` (spec/scoring_v1.json) but the Segment `factors` field is `activity_estimate`. Pick one; I kept `activity` in the config.
2. Scale and bands are not defined: is `score` 0-100? Are `factors` 0-100? What score cutoffs make green / yellow / red? What makes `confidence` high / low?
3. `get_places(area, time)`: `area` has no type (bounding box? route line plus buffer? grid cell?). The cache key's `area_cell` size is also missing.
4. The place shape is not defined in CONTRACTS (name, lat/lng, `open_intervals`, `is_24h`, `category`, `source`, `fetched_at`). Only TECHNICAL_SPEC mentions `open_intervals`. Needs one place model.
5. Errors: no HTTP status per error code (e.g. BAD_REQUEST 400, NO_ROUTE 404, UPSTREAM_TIMEOUT 504) and no catch-all code for unexpected errors.
6. `POST /v1/routes`: allowed `priorities` values are not listed (are they factor names?). `depart_time` timezone handling is not stated. `geometry` is just the words "GeoJSON LineString".
7. Env: Bright Data usually needs more than a key (a zone or dataset name). No variable for it, nor for the allowed CORS origin. `CACHE_TTL_SECONDS` is in .env.example but not in CONTRACTS.
8. TECHNICAL_SPEC mentions `POST /v1/alerts` but CONTRACTS does not. TECHNICAL_SPEC section 9 has stray "```n" characters and section 12 is empty (spec cleanup, not a contract issue).
9. Contract status still says DRAFT v1 awaiting Amey's confirmation; Amey should confirm or request changes (OPEN_QUESTIONS #6).
