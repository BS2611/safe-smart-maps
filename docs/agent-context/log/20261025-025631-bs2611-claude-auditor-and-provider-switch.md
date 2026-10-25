# claude-auditor-and-provider-switch

- When: 2026-10-25
- Who: bs2611 / Bhavpreet (agent: claude-code)
- Branch / commit: bhav/backend-data / see git log
- Files touched: server/services/audit.py (new), server/services/explain.py, server/wiring.py, .env.example, tests/test_audit_and_providers.py (new), DECISIONS.md
- What changed: (1) StreetAuditor: Claude vision call on one photo, strict JSON schema, wording filter, cache by photo id, call cap, returns None on any problem. Needs a PhotoSource; none exists yet, so it is not wired into the planner. (2) OpenAICompatExplainer plus build_explainer() chosen by EXPLAINER_PROVIDER; wiring now uses build_explainer().
- Why: Plan step 6, the parts that need no tokens.
- Decisions made in chat (also added to DECISIONS.md? yes/no): skip token-dependent work for now (yes)
- Contracts affected: none (no response field changed); new env names in .env.example
- How it was tested: pytest 482 passed, ruff clean; model answers are labeled fixtures via httpx.MockTransport. NOT tested live: no real Claude vision call (no sample photo, Pillow not installed) and no real OpenAI-compatible endpoint.
- Unfinished / uncommitted: route analyst (tool use), labeled eval, Mapillary PhotoSource, planner wiring of audits, UI to show photo + audit, transit/Apify.
- Open issues / risks: audit prompt untested on real street photos; model name uses claude-haiku-5-5 default, vision quality may need sonnet-5-5.
- Next step for whoever continues: add a Mapillary PhotoSource (needs token), call StreetAuditor.audit_near for the weakest stretches in planner.plan, surface result as an additive field, then build the eval.
- Needs from teammate: Mapillary token; Amey to review.
