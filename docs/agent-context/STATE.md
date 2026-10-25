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
- Status: Bright Data places live + cached; OSM context provider built (live Overpass check still not done); M3.3 segment scoring and M3.4 continuity/route-level score done and tested (272 tests before Bhavpreet's PR #4; 439 pass now), committed locally on amey/backend, not pushed. Reviewed PR #4 (Mapbox provider): fixed test_wiring .env isolation, added lat/lng guard to segment_route.
- Doing now: Render deployment packaging added for the current backend; Docker and Git verification are pending on a machine with Docker Desktop and Git write access.
- Files in progress: `server/Dockerfile`, `render.yaml`, `.dockerignore` (deployment packaging; review needed)
- Next: confirm `WEB_ORIGINS` and production API keys, run the Docker health check, then commit and push the deployment files for Render auto-deploy.
- Blocked on: this environment cannot write Git refs or access the Docker engine; Amey/backend review is needed before deployment.

## Guide (third person, advice and submission content, little code)
- Owns: Devpost text, demo script, community quotes, track questions (`docs/agent-context/OPEN_QUESTIONS.md`)
- Status:
- Next:

## Shared areas (ask first, log every change)
- `CONTRACTS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `docs/specs/`, `README.md`, `.env.example`, `package.json`
