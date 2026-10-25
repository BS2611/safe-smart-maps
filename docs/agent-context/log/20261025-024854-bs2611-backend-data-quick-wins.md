# backend-data-quick-wins

- When: 2026-10-25 02:48
- Who: bs2611 / Bhavpreet (agent: claude-code)
- Branch / commit: bhav/backend-data (cut from origin/main 6845aee) / see git log
- Files touched: scoring/scoring_v1.json, server/services/geo.py, segment_scoring.py, planner.py, server/wiring.py, tests/fakes.py, tests/test_segment_scoring.py, tests/test_extra_factors.py (new), CONTRACTS.md, DECISIONS.md
- What changed: Four scoring factors now use real inputs: turns (route geometry), activity (open places x time of day, labeled estimate), incidents (SF police reports, last 90 days) and a 311 streetlight-outage penalty on known lighting. SF open data is wired into the planner (cached 6 h; failures become warnings and the factors stay "not sure"). A segment with only the turns factor is still "not sure".
- Why: 20% of the weight was always "not sure" (plan: backend data + Claude upgrade, step 1-2).
- Decisions made in chat (also added to DECISIONS.md? yes/no): do not push to main; push a backend branch, test, then merge; no AI co-author lines; implement current plan scope only (yes, constants recorded in DECISIONS.md)
- Contracts affected: CONTRACTS.md scoring factor notes and the SF open data wiring note (no response field added or removed)
- How it was tested: pytest in the worktree: 468 passed (26 new in tests/test_extra_factors.py, 3 older scorer tests updated), ruff clean. All SF data in tests is a labeled fake (FakeSf). Live check run for a 0.015 deg box near Palace of Fine Arts: 56 incidents and 2 open outages came back and parsed.
- Unfinished / uncommitted: transit (needs 511 token), Apify places fallback (needs token and budget), Mapillary photos (needs token), Claude auditor/analyst/eval and provider interface, web UI for new factors, fixture regeneration, live checks.
- Open issues / risks: SF open data adds two network calls per new area (6 h cache). Web app copy still says some factors are always "not sure" (web/ not touched here).
- Next step for whoever continues: run a live check of get_recent_incidents and get_open_outages for the Palace of Fine Arts box, then start transit once the 511 token exists (server/data/transit.py, wire via Providers).
- Needs from teammate: Amey to review the scoring changes (his files) before merge to main; user to provide 511, Mapillary and Apify tokens.
