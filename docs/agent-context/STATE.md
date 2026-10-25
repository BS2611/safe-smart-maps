# STATE - who is doing what right now

Each person edits ONLY their own section. Keep it short. Update it at the end
of every work block. Agents: also read this before touching any file.

Last full review by a human: (date/time)

## Person A: Bhavpreet (frontend / map)
- Owns (do not edit without asking): `web/`, `docs/agent-context/` entries by A
- Status: Branch `bhav/mapbox-routes` (cut from amey/backend fc503b7) has 2 commits: (1) Mapbox walking-route provider from the handoff doc, (2) the `ui` backend rebuilt on Amey's modules: POST /v1/routes, planner, candidates (detours), continuity, selector, explain, wording, prewarm, SF open data + transit providers (unwired). Full suite green (see the newest log for the count). Frontend (`web/`) still lives only on branch `ui`.
- Doing now: Merged origin/main into bhav/backend-data keeping main's scoring; Mapillary audits, Claude auditor/provider switch, Apify fallback and env profiles re-applied on top (see log 20261025-042439). Not pushed yet.
- Files in progress: none
- Next: copy `web/.env.demo.example` to ignored `web/.env.demo`, add the browser token, then run `npm run dev:local` and `npm run dev:demo` in separate terminals.
- Blocked on: Amey's review; STATE "Last full review by a human" still blank

## Person B: Amey (backend / data)
- Owns (do not edit without asking): `server/`, `scoring/`
- Status: Bright Data places live + cached; OSM context provider built (live Overpass check still not done); M3.3 segment scoring and M3.4 continuity/route-level score done and tested (272 tests before Bhavpreet's PR #4; 439 pass now), committed locally on amey/backend, not pushed. Reviewed PR #4 (Mapbox provider): fixed test_wiring .env isolation, added lat/lng guard to segment_route.
- Doing now: Render deployment packaging is committed on local `main` at `045a8d5`; Docker verification and GitHub/Render setup remain.
- Files in progress: none
- Next: push local `main` to GitHub, configure Render from `render.yaml`, set `WEB_ORIGINS` and production API keys, then run the Docker health check.
- Blocked on: Docker engine is unavailable in this environment; Amey/backend review is needed before deployment.

## Guide (third person, advice and submission content, little code)
- Owns: Devpost text, demo script, community quotes, track questions (`docs/agent-context/OPEN_QUESTIONS.md`)
- Status:
- Next:

## Owner tasks (cursor, on the owner's request)
- Status: Street-level photos on the route detail map, branch `cursor/street-view-01d5`
- Doing now: nothing
- Files in progress: none
- Next: none
- Blocked on: STATE "Last full review by a human" is still blank. Bhavpreet owns `web/`; this edit was an explicit owner task.

## Shared areas (ask first, log every change)
- `CONTRACTS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `docs/specs/`, `README.md`, `.env.example`, `package.json`

## Owner tasks (cursor, web)
- Status: Walking navigation and compass on `cursor/walk-nav-01d5`, merged with main after street view landed. Phone-layout fixes stay on their own PR.
- Doing now: Opening the navigation pull request, then updating the phone-layout branch onto main.
- Files in progress: none
- Next: Review the pull request. A phone build needs the same `BUILD_TARGET=android` and `NEXT_DIST_DIR=.next-android` on both `next build` and `cap sync`, because Next writes that export into `.next-android` rather than `out`.
- Blocked on: STATE "Last full review by a human" is still blank. No Android SDK on the last check, so `gradlew assembleDebug` was not run. WebKit was not launched.
