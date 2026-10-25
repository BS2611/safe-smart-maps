# merge-main-into-watch-integration

- When: 2026-10-25 06:40
- Who: bhavpreet (agent: claude-code)
- Branch / commit: bhav/watch-integration, merge commit fe1c8b2 of origin/main 5d06d41
- Files touched: merge only; docs conflicts in DECISIONS.md and STATE.md resolved by keeping both sides (STATE 'Doing now' lines joined into one). No code conflicts.
- What changed: Brought the branch up to date with main (backend-data, walking navigation, compass, phone layout fixes, street view) while keeping the whole watch system.
- Why: Main moved 23 commits; the watch work must sit on top of it before the PR.
- Decisions made in chat (also added to DECISIONS.md? yes/no): none
- Contracts affected: none
- How it was tested: pytest 537 passed. Web: npm test 287 passed (32 files), typecheck clean, lint clean after npm install (main added mapillary-js). Playwright 58 passed, 2 failed on iphone-webkit only (planDemoTrip click timeout in flow 'server problem' and a11y 'results, details'); both pass when run alone, so load flakiness on this laptop. ruff: 1 import-order error in tests/test_gtfs.py (from main commit ad8c879, not watch code) and docs/pitch/build_overview.py (untracked, not committed). Watch Gradle tests not rerun (watch/ unchanged by the merge).
- Unfinished / uncommitted: untracked docs/pitch/ and a pitch log entry from another session were left alone
- Open issues / risks: Phone web screen not yet tested against the real watch; Render needs the merge to main plus redeploy, and WEB_ORIGINS must include the phone origins.
- Next step for whoever continues: Open the PR bhav/watch-integration -> main, then test the phone Watch screen with the watch (watch/README.md steps 2-7). Fix tests/test_gtfs.py import order if CI runs ruff.
- Needs from teammate: Amey: review server/api/watch.py and watch_relay.py
