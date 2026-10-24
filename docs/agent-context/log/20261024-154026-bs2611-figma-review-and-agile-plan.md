# Figma review and agile plan

- When: 2026-10-24 16:00 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: bhav/initial-kit-and-specs / see git log
- Files touched: docs/design/FIGMA_REVIEW.md, docs/design/FIGMA_FIXES_BRIEF.md, docs/specs/AGILE_PLAN.md (new); docs/specs/TASKS.md (rewritten by sprint); AGENTS.md (DoD pointer, file map); DECISIONS.md, OPEN_QUESTIONS.md (15-17), STATE.md
- What changed: Reviewed the 6 Figma frames (file vRgsr90ax1IwDkiisf89lh) against brief, specs, CONTRACTS and rules. Wrote findings (15 must-fix items, 6 scope decisions, missing screens, polish). Wrote agile plan: 3-hour sprints S0-S5, Definition of Done, test strategy (pytest, Vitest/RTL, Playwright Chromium+WebKit at 390/360, contract tests, @live check, CI gates).
- Why: Bhavpreet asked for a design review and an agile build plan with mandatory unit tests and regression, all green.
- Decisions made in chat (also added to DECISIONS.md? yes): agile cadence, DoD, test stack, Figma must-fix gate. "Next year" was voice-typing error: start now.
- Contracts affected: none.
- How it was tested: Figma read via MCP (metadata + 6 screenshots); docs re-checked against CONTRACTS; no code or CI exists yet.
- Unfinished / uncommitted: Figma file not edited (read-only review). .cursor/settings.json is untracked and not mine; left out of the commit.
- Open issues / risks: only 6 of 11 screens exist, core Results screen missing. Test stack and CI are plans, not yet set up (story 0.4). 17 hours is tight; stretch is likely cut.
- Next step for whoever continues: Bhavpreet applies docs/design/FIGMA_FIXES_BRIEF.md in Figma; Amey confirms CONTRACTS v1; then do S0 stories in docs/specs/TASKS.md (repo + CI first).
- Needs from teammate: Amey: confirm CONTRACTS v1, answer OPEN_QUESTIONS 5, 6, 13, 14.
