# transit-mapillary-audits-apify

- When: 2026-10-25 03:27
- Who: bs2611 / Bhavpreet (agent: claude-code)
- Branch / commit: bhav/backend-data / see git log
- Files touched: server/data/transit.py (rewritten), mapillary.py (new), apify.py (new); server/services/audit.py, planner.py, schemas.py, segment_scoring.py, prefetch.py; server/wiring.py; scoring/scoring_v1.json; .env.example; scripts/mapillary_coverage.py; tests (test_transit, test_mapillary, test_apify, test_planner_audits, fakes); CONTRACTS.md, DECISIONS.md
- What changed: (1) Transit factor from the live 511 StopMonitoring feed (only for arrival times within ~30 min of now, else "not sure"). (2) Mapillary photo source plus Claude audits of up to 3 weak/not-sure stretches on the first route, returned as additive `street_photo_audits`; never changes scores. (3) Apify places fallback used only when Bright Data fails. (4) Auditor cap is now a lifetime guard (AUDIT_MAX_CALLS_TOTAL); per-request limit is AUDIT_MAX_CALLS_PER_REQUEST.
- Why: Plan steps 3-6 now that the tokens exist.
- Decisions made in chat (also added to DECISIONS.md? yes/no): yes (3 lines in DECISIONS.md)
- Contracts affected: CONTRACTS.md route result gained `street_photo_audits`; transit factor and env names documented. Web zod ignores extra fields; the UI does not show audits yet.
- How it was tested: pytest 520 passed, ruff clean (labeled fixtures for all APIs). LIVE: 511 returned 1026 arrivals for the next 30 min; Mapillary photo + Claude vision returned a valid reading; Apify returned 3 real places with hours that the parser reads; full POST /v1/routes through the real app returned 200 with transit known on 44 of 82 segments, incidents on all 82, and 3 photo audits. NOT live-tested: the Apify fallback inside a real Bright Data failure; Render deploy.
- Unfinished / uncommitted: web UI for audits/photos and the new factors; tool-use route analyst; labeled eval; stop-timetable (planning hours ahead) for transit.
- Open issues / risks: Mapillary coverage is only 25-35% of sample points (recent flat photo within 40 m); lighting was "not sure" on all 82 segments of the live trip (OSM has no lit tags there), so photos are the only lighting hint; this local run had no saved places, so open_places/activity were not sure; audits add a few seconds to a request (parallel Claude calls) and cost a few cents.
- Next step for whoever continues: show `street_photo_audits` on Route detail in web/ (labeled, with attribution), then decide on the eval. Amey to review scoring_v1.json, planner.py, segment_scoring.py.
- Needs from teammate: Amey review before merge to main.
