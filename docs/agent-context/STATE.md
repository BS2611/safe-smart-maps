# STATE - who is doing what right now

Each person edits ONLY their own section. Keep it short. Update it at the end
of every work block. Agents: also read this before touching any file.

Last full review by a human: (date/time)

## Person A: Bhavpreet (frontend / map)
- Owns (do not edit without asking): `web/`, `docs/agent-context/` entries by A
- Status: Mapbox walking-route provider done on branch `bhav/mapbox-routes` (cut from amey/backend fc503b7): server/data/mapbox.py, 41 mocked tests, one live call OK. Full suite 270 passed. Frontend and the rest of the backend built earlier live on branch `ui` (not yet on the backend branch).
- Doing now: porting the `ui` backend (routes API, planner, continuity, selector) onto `bhav/mapbox-routes` as a second commit
- Files in progress: `server/` and `tests/` on branch bhav/mapbox-routes only (a separate worktree)
- Next: finish the port, run the full suite, push `bhav/mapbox-routes`, then Amey reviews/merges
- Blocked on: nothing

## Person B: Amey (backend / data)
- Owns (do not edit without asking): `server/`, `scoring/`
- Status: Bright Data places live + cached; OSM context provider built (live Overpass check still not done); M3.3 segmenter + segment scoring done and tested (229 tests pass), committed locally on amey/backend, not pushed.
- Doing now: nothing
- Files in progress: none
- Next: M3.4 continuity rule (server/services/continuity.py); retry live Overpass check; then selector and /v1/routes when Mapbox provider lands
- Blocked on: Mapbox candidate-route provider (other developer) for /v1/routes; approval to add Place model to CONTRACTS.md

## Guide (third person, advice and submission content, little code)
- Owns: Devpost text, demo script, community quotes, track questions (`docs/agent-context/OPEN_QUESTIONS.md`)
- Status:
- Next:

## Shared areas (ask first, log every change)
- `CONTRACTS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `docs/specs/`, `README.md`, `.env.example`, `package.json`
