# STATE - who is doing what right now

Each person edits ONLY their own section. Keep it short. Update it at the end
of every work block. Agents: also read this before touching any file.

Last full review by a human: (date/time)

## Person A: Bhavpreet (frontend / map)
- Owns (do not edit without asking): `web/`, `docs/agent-context/` entries by A
- Status: specs drafted (functional, technical, tasks); no code yet
- Doing now: aligning specs with the agent kit
- Files in progress: none
- Next: agree folder layout + contract with Amey; git init and commit
- Blocked on: Amey's answers (framework, layout, contract shape)

## Person B: Amey (backend / data)
- Owns (do not edit without asking): `server/`, `scoring/`
- Status: Bright Data places provider LIVE-VERIFIED 2026-10-24 (repo smoke test passed end to end, 19 places in the Palace box; earlier raw call, 60 records, all normalized, 59 with parsed hours). 148 unit tests pass on amey/backend (local commits, not pushed). See log *brightdata-live-verification.
- Doing now: nothing
- Files in progress: none
- Next: cache/prefetch layer for Bright Data places (a call takes 60+ s); decide the 8 open behaviors in the 20261024-174045 log; then OSM/Mapbox or segment scoring
- Blocked on: approval to add Place model to CONTRACTS.md

## Guide (third person, advice and submission content, little code)
- Owns: Devpost text, demo script, community quotes, track questions (`docs/agent-context/OPEN_QUESTIONS.md`)
- Status:
- Next:

## Shared areas (ask first, log every change)
- `CONTRACTS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `docs/specs/`, `README.md`, `.env.example`, `package.json`
