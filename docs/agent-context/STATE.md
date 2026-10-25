# STATE - who is doing what right now

Each person edits ONLY their own section. Keep it short. Update it at the end
of every work block. Agents: also read this before touching any file.

Last full review by a human: (date/time)

## Person A: Bhavpreet (frontend / map)
- Owns (do not edit without asking): `web/`, `docs/agent-context/` entries by A
- Status: Branch `bhav/mapbox-routes` (cut from amey/backend fc503b7) has 2 commits: (1) Mapbox walking-route provider from the handoff doc, (2) the `ui` backend rebuilt on Amey's modules: POST /v1/routes, planner, candidates (detours), continuity, selector, explain, wording, prewarm, SF open data + transit providers (unwired). Full suite green (see the newest log for the count). Frontend (`web/`) still lives only on branch `ui`.
- Doing now: nothing running; waiting for Amey's review
- Files in progress: none
- Next: Amey reviews `bhav/mapbox-routes`; then push/PR as agreed; re-point `web/` at the new response (segment ids are `seg-<n>`, `via` is empty, extra fields `unknown_factors`, `known_weight_fraction`); live check `python -m pytest -m live`
- Blocked on: Amey's review; STATE "Last full review by a human" still blank

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
