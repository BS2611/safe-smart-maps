# verify-backend-scaffold

- When: 2026-10-24 12:54 PT
- Who: Amey (agent: claude-code)
- Branch / commit: amey/backend-scaffold / committed together with this log (hash in git log)
- Files touched: this log; docs/agent-context/STATE.md (Amey section only). No code changed.
- What changed: Amey re-issued the backend scaffold task (steps 1-5). All of it was already done in commit 36cf627 (log 20261024-124148-amey-backend-scaffold.md). This session checked each step against the code and ran it again instead of rebuilding.
- Why: Confirm that the scaffold matches the task and still runs, and avoid duplicate work.
- Decisions made in chat (also added to DECISIONS.md? no): none new. FastAPI is still not in DECISIONS.md (shared file, out of scope for this task).
- Contracts affected: none. CONTRACTS.md was not edited.
- Step-by-step check:
  1. scoring/scoring_v1.json matches TECHNICAL_SPEC section 3 exactly. Weights sum to 1.0. CONTRACTS.md only sets the path and the "sum to 1.0" rule, so the values do not conflict. The only conflict is a name: `activity` in the spec and config vs `activity_estimate` in CONTRACTS `factors` (item 1 below). It was not guessed; the config keeps the spec name.
  2. FastAPI scaffold: server/api/health.py -> server/services/health.py. server/data/ has the providers. The startup check is in server/services/scoring_config.py, called from the lifespan in server/main.py. server/requirements.txt exists.
  3. server/data/places.py has the abstract PlacesProvider.get_places(area, time). server/data/brightdata.py has a stub that raises NotImplementedError. No fake data.
  4. The Bright Data call was skipped because there is no key (see Unfinished).
  5. CONTRACTS review: see Needs from teammate.
- How it was tested (all run this session):
  - `.venv/bin/python -c "...sum(weights)..."` printed `sum 1.0`.
  - `.venv/bin/uvicorn server.main:app --port 8000` then `curl -i localhost:8000/v1/health` returned `HTTP/1.1 200 OK` and `{"status":"ok","api_version":"1"}`. The server log showed "Application startup complete". The server was stopped afterwards.
  - Ran load_scoring_config on a temp copy with turns=0.10. It raised `ScoringConfigError: scoring_v1: weights sum to 1.05, expected 1.0`. The real file was not touched.
  - Called BrightDataPlacesProvider().get_places(None, None). It raised `NotImplementedError: Bright Data fetching is not implemented yet`.
  - No unit test files exist yet.
- Run command:
  python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt && .venv/bin/uvicorn server.main:app --reload --port 8000
  then: curl localhost:8000/v1/health
- Unfinished / uncommitted:
  - The real Bright Data call has not been made because there is no key. BrightDataPlacesProvider.get_places is still a stub.
  - `.env.example` has no Bright Data zone or dataset variable yet. It was not added because the exact name depends on which Bright Data product is used (see item 7).
- Open issues / risks:
  - `git pull --rebase` says the branch has no upstream. The branch has not been pushed.
  - FastAPI is in use but not yet recorded in DECISIONS.md, and OPEN_QUESTIONS #5 and #6 are still open. Amey needs to add these or approve the edit, because they are shared files.
  - Scoring scale, bands and confidence rules are undefined, which blocks the scoring service (item 2).
- Next step for whoever continues: Put BRIGHTDATA_API_KEY (and zone/dataset if needed) in .env, never git. Implement BrightDataPlacesProvider.get_places in server/data/brightdata.py with httpx. Make one real call for a business near Palace of Fine Arts and print its name, opening hours and fetched_at.
- Needs from teammate (CONTRACTS.md review, file not edited; same 9 items as 20261024-124148, still open):
  1. Weight key `activity` (spec, config) vs `factors.activity_estimate` (CONTRACTS). Pick one.
  2. The 0-100 scale for `score` and `factors`, the band cutoffs for green, yellow and red, and the confidence high/low rule are not defined.
  3. The type of `area` in get_places is not defined, and neither is the `area_cell` size for the cache key.
  4. The place model is not in CONTRACTS (name, lat/lng, open_intervals, is_24h, category, source, fetched_at).
  5. Error codes have no HTTP status mapping and there is no catch-all code for unexpected errors.
  6. The allowed `priorities` values, how `depart_time` time zones are handled, and the `geometry` encoding are not stated.
  7. There is no env var for the Bright Data zone or dataset or for the CORS origin. `CACHE_TTL_SECONDS` is in .env.example but not in CONTRACTS.
  8. TECHNICAL_SPEC has `POST /v1/alerts` but CONTRACTS does not. TECHNICAL_SPEC section 9 has stray characters and section 12 is empty.
  9. CONTRACTS still says "DRAFT v1"; Amey has to confirm it.
