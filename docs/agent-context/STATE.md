# STATE - who is doing what right now

Each person edits ONLY their own section. Keep it short. Update it at the end
of every work block. Agents: also read this before touching any file.

Last full review by a human: (date/time)

## Person A: Bhavpreet (frontend / map)
- Owns (do not edit without asking): `web/`, `docs/agent-context/` entries by A
- Status: specs, Stitch brief, Figma review (docs/design/FIGMA_REVIEW.md) and agile plan (docs/specs/AGILE_PLAN.md) done; no code yet
- Doing now: Sprint 0: CI + test scaffolding done on branch bhav/s0-test-ci-scaffold (needs push + PR); next fix Figma list
- Files in progress: none (web/ scaffold, tests/test_health.py, tests/test_scoring_config.py, CI files are committed on s0 branch)
- Next: tick the must-fix list in docs/design/FIGMA_REVIEW.md; answer OPEN_QUESTIONS 10, 11, 15-17; create GitHub repo; start S0 in TASKS.md
- Blocked on: Amey confirming CONTRACTS v1 (see his latest log)

## Person B: Amey (backend / data)
- Owns (do not edit without asking): `server/`, `scoring/`
- Status: M2.2/M2.3 code done on amey/brightdata-places (Place model, Bright Data provider, open/closed/unknown evaluator, 16 unit tests passing). Live Bright Data call NOT run: no key.
- Doing now: nothing
- Files in progress: none (web/ scaffold, tests/test_health.py, tests/test_scoring_config.py, CI files are committed on s0 branch)
- Next: put BRIGHTDATA_API_KEY in .env, run `.venv/bin/python -m scripts.brightdata_smoke`, check real open_hours shape; then Mapbox/OSM
- Blocked on: Bright Data API key; CONTRACTS.md items in the log (incl. approving Place model)

## Guide (third person, advice and submission content, little code)
- Owns: Devpost text, demo script, community quotes, track questions (`docs/agent-context/OPEN_QUESTIONS.md`)
- Status:
- Next:

## Shared areas (ask first, log every change)
- `CONTRACTS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `docs/specs/`, `README.md`, `.env.example`, `package.json`
