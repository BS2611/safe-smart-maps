# S0: test and CI scaffolding

- When: 2026-10-24 16:25 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: bhav/s0-test-ci-scaffold / see git log (includes merge of origin/main = Amey's PR #1 and #2)
- Files touched: pyproject.toml, requirements-dev.txt, tests/test_health.py, tests/test_scoring_config.py (new); web/ (new: Next.js 15 app, Vitest, Playwright, lib/wording.ts, copy test, DisclaimerBanner); .github/workflows/ci.yml, scripts/check-secrets.sh (new); .gitignore; DECISIONS.md, STATE.md
- What changed: Stories 0.4 (CI skeleton) and part of 0.5 done. Backend: pytest + coverage gate 80% + ruff, tests for /v1/health and scoring_v1 (weights, thresholds, bad config rejected). Frontend: Vitest + RTL, Playwright on iPhone WebKit, Pixel Chromium and 360x640, an automated wording test that fails on "safe/safest/hazard/dangerous/crime-free" in UI source. CI jobs: backend, frontend (lint, types, tests with coverage gate, build), e2e, secrets scan.
- Why: Sprint 0 of docs/specs/AGILE_PLAN.md; DoD needs tests and regression gates before feature work.
- Decisions made in chat (also added to DECISIONS.md? yes): test layout, wording test, frontend stack.
- Contracts affected: none.
- How it was tested (all run this session, all green): pytest 25 passed, backend coverage 81.2%; ruff clean; vitest 19 passed, 100% on lib/components; tsc clean; next lint clean; next build OK; Playwright 6 passed (3 viewports x 2 tests); check-secrets.sh OK and it fails correctly on a planted fake key (removed). CI itself has NOT run yet (needs a push and a PR on GitHub); workflow YAML parsed OK locally.
- Findings: (1) Amey's code needs the tzdata package on Windows (zoneinfo America/Los_Angeles failed at import); added tzdata to requirements-dev.txt; Amey should add it to server/requirements.txt. (2) ruff flagged Amey's tests/test_places.py (import order) and scripts/brightdata_smoke.py (B904); I did not edit his files, I added per-file ignores in pyproject.toml with a note to remove them. (3) Wording test caught the CSS "safe-area" as a false positive; allowed that term explicitly.
- Unfinished / uncommitted: branch not pushed; no PR. Branch protection (required checks) must be set in GitHub settings by the repo owner after the first CI run. Playwright WebKit on Windows is not identical to real iOS Safari: still need a real iPhone check.
- Open issues / risks: node 24 and Playwright browsers were installed locally; first CI run may need small fixes (apt deps, caching). Coverage gate for scoring/continuity/selector at 100% is not enforced yet because the modules do not exist; add when they land. No frontend coverage threshold on app/ (only components/ and lib/).
- Next step for whoever continues: push bhav/s0-test-ci-scaffold, open a PR into main, check the CI run, then enable branch protection with the 4 checks (backend, frontend, e2e, secrets) and 1 review. Amey: add tzdata to server/requirements.txt and fix the two ruff items, then delete the per-file ignores.
- Needs from teammate: Amey: review this PR, tzdata + ruff fixes.
