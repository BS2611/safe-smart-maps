# bring-brightdata-fix-into-ui

- When: 2026-10-24 18:45
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: ui
- Files touched: server/data/brightdata.py, server/data/opening_hours.py, tests/test_brightdata_live_shape.py, tests/test_brightdata_normalization.py, tests/test_opening_hours.py, tests/test_provider_failures.py, tests/fixtures/brightdata_live_shape_sample.json, docs/agent-context/BRIGHTDATA.md (all copied unchanged from origin/amey/backend f5dd488)
- What changed: `ui` was cut before Amey's Bright Data fixes, so get_places always failed on HTTP 202. Copied his fixed provider, hours parser and tests into ui. Nothing edited by hand.
- Why: the earlier "live call blocked" finding was this stale copy. Amey's 95ac654 already had 202 polling, blank-dataset-id fallback and lat/lon.
- Decisions made in chat (also added to DECISIONS.md? yes/no): none
- Contracts affected: none
- How it was tested: pytest -m "not live": 271 passed. LIVE: scripts.brightdata_smoke returned 16 real places with open/closed/unknown.
- Unfinished / uncommitted: a full merge of origin/amey/backend into ui was NOT done: it conflicts in tests/test_health.py, tests/test_scoring_config.py, STATE.md, DECISIONS.md (both sides rewrote them). Needs a human decision.
- Open issues / risks: a live fetch takes 30-60 s; first demo request is slow unless PREWARM_DEMO is on. pytest -m live not run yet.
- Next step for whoever continues: run `.venv/Scripts/python -m pytest -m live`; then merge amey/backend into ui and resolve the 4 conflicts with Amey.
- Needs from teammate: Amey: help resolve the 4 merge conflicts.
