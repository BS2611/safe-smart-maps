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
- Status: Bright Data places provider, Place model, hours evaluator merged. 140 unit tests pass on amey/backend (local commit, not pushed). Live Bright Data call NOT run: no key. Provider and normalization are unit-tested only; real network integration unverified.
- Doing now: nothing
- Files in progress: none
- Next: decide the 8 open behaviors in the 20261024-174045 log; put BRIGHTDATA_API_KEY in .env, run `.venv/bin/python -m scripts.brightdata_smoke`, check real open_hours shape; then Mapbox/OSM or segment scoring
- Blocked on: Bright Data API key; approval to add Place model to CONTRACTS.md

## Guide (third person, advice and submission content, little code)
- Owns: Devpost text, demo script, community quotes, track questions (`docs/agent-context/OPEN_QUESTIONS.md`)
- Status:
- Next:

## Shared areas (ask first, log every change)
- `CONTRACTS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`, `docs/specs/`, `README.md`, `.env.example`, `package.json`
