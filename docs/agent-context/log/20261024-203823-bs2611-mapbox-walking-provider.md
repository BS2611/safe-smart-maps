# mapbox-walking-provider

- When: 2026-10-24 20:45 PT
- Who: bs2611 / Bhavpreet (agent: claude-code)
- Branch / commit: bhav/mapbox-routes (cut from origin/amey/backend fc503b7) / see commit 1
- Files touched: server/data/mapbox.py (new), tests/test_mapbox_provider.py (new), tests/fixtures/mapbox_directions_sample.json (new), scripts/mapbox_smoke.py (new), docs/agent-context/CONTRACTS.md, DECISIONS.md, STATE.md, this log
- What changed: Mapbox Directions (walking) candidate provider. start + destination -> `RouteCandidate(id, provider="mapbox", coordinates[(lng, lat)], distance_m, duration_s)`. No scoring or ranking. Own `MapboxError` (kind failed/timeout/not_configured/empty). `RouteCandidate.as_lat_lng()` gives the (lat, lng) order the segmenter uses.
- Why: Handoff doc "Safe Smart Maps Mapbox Backend Handoff": Amey's /v1/routes is blocked on routing candidates.
- Decisions made in chat (also added to DECISIONS.md? yes/no): work happens on a new branch cut from the latest amey/backend (not on amey/backend itself); the earlier `ui` backend is brought over in a second commit; yes, the design decision is in DECISIONS.md
- Contracts affected: CONTRACTS.md new section "Routing provider (server/data/mapbox.py)" and the Data source interface line about the routing provider
- How it was tested: baseline on fc503b7 = 229 passed. After adding the Mapbox tests: 270 passed (41 new tests + 54 subtests, all mocked via httpx.MockTransport, no network). Mutation check: reversing as_lat_lng, removing the latitude range check, changing alternatives, leaking the exception text, shifting ids each made tests fail. ruff (E,F,I,B, line 100) clean on new files. ONE live call (scripts/mapbox_smoke.py, Palace of Fine Arts -> Montgomery BART): 1 route, 5533 m, 3985 s, 377 coordinates, first point is (lng, lat) in San Francisco. Token never printed.
- Unfinished / uncommitted: nothing for this part. Part 2 (port of the `ui` backend) is the next log entry.
- Open issues / risks: Mapbox returned only ONE route even with alternatives=true (walking profile often does). Candidates 2-3 need detour waypoints, which the `ui` branch has (server/data/mapbox.py on ui, detour_points + dedupe); not part of this commit. `ui` also has its own osm.py, segmenter, scoring and geo that overlap Amey's new modules: see the next log.
- Next step for whoever continues: Amey can call `MapboxWalkingProvider().get_walking_routes((lng, lat), (lng, lat))` and pass `route.as_lat_lng()` to `segment_route(...)`. Test command: `python -m pytest -q` (270 passed). Live check: `python -m scripts.mapbox_smoke` (needs MAPBOX_TOKEN in .env).
- Needs from teammate: Amey, please confirm the contract section in CONTRACTS.md (esp. (lng, lat) order and error kinds).
