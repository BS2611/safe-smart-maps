# Initial functional spec, technical spec, task breakdown

- When: 2026-10-24 10:56 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: none (folder is not a git repo yet) / uncommitted
- Files touched: safe-smart-maps/docs/FUNCTIONAL_SPEC.md, TECHNICAL_SPEC.md, TASKS.md, DECISIONS.md (new); docs/agent-context/STATE.md, DECISIONS.md (updated)
- What changed: Wrote first drafts of the specs and task breakdown from Safe_Smart_Maps_Team_Plan.pdf. Chose Next.js frontend, Python backend (FastAPI proposed, Django open), 3-layer architecture, community = students leaving a campus late.
- Why: Give both people and all agents one written plan before coding starts.
- Contracts affected: none edited, but CONFLICTS exist (see Open issues). CONTRACTS.md was not changed.
- How it was tested: not tested (docs only, no code).
- Open issues / risks:
  - Folder layout mismatch: kit says `web/`, `server/`, `scoring/`; TECHNICAL_SPEC §9 says `frontend/`, `backend/`, `config/`. Needs one choice.
  - API mismatch: CONTRACTS says `POST /routes`; TECHNICAL_SPEC says `POST /v1/routes` with `api_version`/`scoring_version` fields.
  - Shape mismatch: CONTRACTS Route result uses `route_score`, `continuity{}`, `distance_m`, `segment_id`, `start/end`, `confidence high|low|unknown`; TECHNICAL_SPEC uses `score`, flat `coverage`/`longest_gap_m`, `index`, `band`, `confidence ok|low|unknown`.
  - Env var names: CONTRACTS says MAPBOX_TOKEN; TECHNICAL_SPEC uses server/public Mapbox tokens.
  - Config path: CONTRACTS `scoring/scoring_v1.json`; TECHNICAL_SPEC `config/scoring_v1.json`.
  - Duplicate decision files: safe-smart-maps/docs/DECISIONS.md (open questions) vs docs/agent-context/DECISIONS.md (append-only log).
  - Kit sits at CalHack_13 root while specs sit in safe-smart-maps/; repo root not chosen.
- Next step for whoever continues: Both humans agree layout and contract (CONTRACTS.md is source of truth), then align TECHNICAL_SPEC to it; git init, set user.name, commit kit.
- Needs from teammate: Amey to confirm backend framework, folder names, and the contract shape.
