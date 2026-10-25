# review-fixes-test-isolation-lat-lng-guard

- When: 2026-10-24 (evening PT)
- Who: Amey (agent: claude-code)
- Branch / commit: amey/backend / see git log (one commit with this log)
- Files touched: tests/test_wiring.py, server/services/segmenter.py, tests/test_segmenter.py, docs/agent-context/CONTRACTS.md (one line), docs/agent-context/STATE.md (Amey section), this log
- What changed: (1) Reviewed Bhavpreet's Mapbox provider (already merged via PR #4): no critical/high findings, one real Mapbox request normalized and fed segment_route -> SegmentScorer -> compute_continuity fine. (2) Test isolation: the `clean_app` fixture in tests/test_wiring.py now patches `server.main.load_dotenv` to a no-op, so the app lifespan cannot put MAPBOX_TOKEN / ANTHROPIC_API_KEY / BRIGHTDATA_API_KEY back from the repo-root .env. (3) `segment_route` now raises ValueError for any point outside lat -90..90 / lng -180..180 (NaN too), before any geometry. It never swaps or guesses order; Mapbox points still go through RouteCandidate.as_lat_lng().
- Why: before the fix, the 503 test returned 200 on a machine with a real .env, i.e. it made real Mapbox/Overpass/Anthropic calls. A forgotten (lng, lat) swap used to produce plausible-looking wrong segments with no error.
- Decisions made in chat (also added to DECISIONS.md? yes/no): fix the test not production; reject, never auto-swap, invalid coordinates. Both small; not added to DECISIONS.md (recorded here and in CONTRACTS.md).
- Contracts affected: CONTRACTS.md "Segment scoring" segmenter input line: invalid lat/lng raises ValueError.
- How it was tested: pytest with a temporary socket/DNS guard plugin (not committed; self-test proved it catches a real attempt). test_wiring.py 3 passed; Bhavpreet-added tests 158 passed; full default suite 439 passed, 3 live deselected, 0 network attempts recorded. 439 = 430 existing + 9 new segmenter tests. ruff clean on changed files. NOTE: before this fix, my review runs of the old test (3 runs) did hit real Mapbox and probably Overpass/Anthropic.
- Unfinished / uncommitted: none. Not pushed.
- Open issues / risks: unchanged and deliberately untouched: Mapbox duration (~1.26 m/s) vs 1.4 m/s arrival assumption; candidate id renumbering after dedupe (docstring in mapbox.py says ids never shift); up to 3 sequential Mapbox calls at 12 s timeout each; mapbox_directions_sample.json distance_m (5121) does not match its 7-point geometry (~4620 m).
- Next step for whoever continues: decide push of amey/backend (4 merge commits + this one ahead of origin) and the frontend re-point to the new /v1/routes response; then live check `python -m pytest -m live` by hand.
- Needs from teammate: Bhavpreet: FYI his tests/test_wiring.py fixture and the segmenter guard changed; web/ must send (lat, lng) as before.
