# windows-utf8-fixture-read

- When: 2026-10-24 18:40
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: bhav/brightdata-setup, pushed to amey/backend
- Files touched: tests/test_brightdata_live_shape.py (one line), this log
- What changed: fixture is now read with encoding="utf-8". On Windows the default encoding garbled the en dash and test_narrow_nbsp_hours_parse_and_evaluate failed (148 pass now; 147 + 1 fail before).
- Why: Bhavpreet asked for 202 polling. I wrote it, then found Amey's 95ac654 already has 202 polling, the blank dataset id fix and lat/lon. I dropped my duplicate code, kept his, did not push mine.
- Decisions made in chat (also added to DECISIONS.md? yes/no): none
- Contracts affected: none
- How it was tested: pytest tests: 148 passed. My own live smoke run (before dropping my copy) returned 19 places; it matched what Amey reports.
- Unfinished / uncommitted: none
- Open issues / risks: live fetch takes 30-60 s: prefetch and cache the demo area. Open hours "unknown" for some places: check missing data vs parser gap.
- Next step for whoever continues: Amey: wire the provider through server/data/cache.py with a prefetch for the demo area.
- Needs from teammate: none
