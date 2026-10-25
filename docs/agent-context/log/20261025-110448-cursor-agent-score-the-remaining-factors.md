# score the remaining factors

- When: 2026-10-25 04:04 PT
- Who: owner via cursor (agent: cursor)
- Branch / commit: cursor/score-factors-01d5 / this commit
- Files touched: scoring/scoring_v1.json, server/services/segment_scoring.py, server/services/planner.py, server/wiring.py, server/data/models.py, server/data/osm.py, server/data/gtfs.py, tests/test_factor_scores.py, tests/test_demo_corridor.py, tests/test_segment_scoring.py, tests/test_planner.py, tests/fixtures/gtfs_demo/, web/lib/scoring-info.ts, web/components/HowScoresScreen.tsx, web/components/DetailCompareHow.test.tsx, .env.example, docs/agent-context/CONTRACTS.md, docs/agent-context/DECISIONS.md
- What changed: Turns, activity, incidents, and transit are scored from the route shape, OSM, SF open data, and a GTFS feed. Lighting also uses street lamps and open 311 outages, and a missing lit tag stays not sure. Open places still use hours at the segment arrival time. Weights were retuned in scoring_v1.json. The score page lists the same weights.
- Why: Those four factors were in the config but always "not sure". The owner asked for real public-data scoring before the 9 AM PT deadline.
- Decisions made in chat (also added to DECISIONS.md? yes): Weights and the per-factor rules are the 2026-10-25 03:55 line in DECISIONS.md. No Bright Data key was committed.
- Contracts affected: CONTRACTS.md segment-scoring bullets and GTFS_DIR. Factor names and the 0-100-or-null shape did not change.
- How it was tested: python3 -m pytest tests (456 passed), python3 -m ruff check server tests (clean), npm test (206 passed), npm run lint (clean), npm run typecheck (clean), NEXT_DIST_DIR=.next-e2e playwright Chromium on Pixel 7 and 360px (production build, 36 passed).
- Unfinished / uncommitted: docs/hackathon/ was not touched. .env is gitignored. web/tsconfig.json was restored after the Next build. A live Bright Data fetch and a live Muni/BART download were not run; GTFS_DIR empty means transit stays not sure.
- Open issues / risks: STATE.md "Last full review by a human" is still blank. Frequency-based GTFS trips count as in service for the whole headway window, not a single clock time. WebKit e2e was not run on this machine.
- Next step for whoever continues: Put an extracted SF Muni or BART GTFS folder in GTFS_DIR (name only is in .env.example) and restart the API. Do not commit the feed or any API key.
- Needs from teammate: none
