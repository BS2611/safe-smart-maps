# Harden agent kit and unify layout

- When: 2026-10-24 11:06 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: no-git / uncommitted
- Files touched: AGENTS.md, CLAUDE.md, README_FIRST.md, .cursor/rules/team-rules.mdc, .claude/settings.json, scripts/new-log.sh, scripts/new-log.ps1, scripts/context-brief.sh, docs/agent-context/{CONTRACTS,STATE,DECISIONS,OPEN_QUESTIONS}.md, log/_TEMPLATE.md, docs/specs/*, .gitignore, .env.example
- What changed: Moved specs to docs/specs/ (removed safe-smart-maps/). CONTRACTS.md rewritten as source of truth (adds /v1, versions, band, reasons). TECHNICAL_SPEC now points to CONTRACTS and uses web/ server/ scoring/. AGENTS.md adds file map, precedence, in-session checkpoints, handoff protocol, stale-STATE check. New context-brief.sh (auto-run by Claude Code SessionStart hook). Log scripts work without git; PowerShell version added. Template gained "Decisions made in chat" and "Unfinished".
- Why: Bhavpreet asked for context never to be lost between agents/people; chose full authority to change anything.
- Decisions made in chat (also added to DECISIONS.md? yes): layout/contract precedence, checkpoint + handoff rules.
- Contracts affected: whole CONTRACTS.md (draft v1: /v1/routes, api_version, scoring_version, band, reasons, also_labels, extra_min, nearest_help_point, env names).
- How it was tested: ran context-brief.sh and both new-log scripts (outputs correct, test logs deleted). Hook and Cursor/Codex behavior not tested.
- Unfinished / uncommitted: nothing committed; folder is not a git repo.
- Open issues / risks: Amey has not confirmed CONTRACTS v1 or FastAPI. Hook needs bash on PATH (Git Bash). Other tools rely on the start prompt, not hooks. Log person name falls back to Windows username (bs2611) until git user.name is set.
- Next step for whoever continues: git init at CalHack_13, set git config user.name, commit, push to GitHub; Amey reviews CONTRACTS.md and answers OPEN_QUESTIONS #5/#6; then start M1 in docs/specs/TASKS.md.
- Needs from teammate: Amey to confirm CONTRACTS v1, backend framework, and set git user.name.
