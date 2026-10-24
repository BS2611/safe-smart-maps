# Agent collaboration kit

Goal: two people (plus a guide), many AI agents (Claude Code, Cursor, Codex),
no shared chat. The repo files carry the memory. Every agent reads them first,
writes to them while working, and writes a log entry last, so any agent or
person can pick up cold.

## Set up (once)
1. Put this folder at the repo root (keep the dot folders `.cursor/`, `.claude/`).
2. `git init` (if needed), `git config user.name "<your name>"` (the log script uses it), then  
   `git add -A && git commit -m "Add agent kit and specs" && git push`.
3. The other person: `git pull`, set `git config user.name`.
4. Each person fills their section of `docs/agent-context/STATE.md` and sets "Last full review".

## Folder map
| Path | Purpose |
|---|---|
| `AGENTS.md` | The rules. One source of truth. |
| `CLAUDE.md`, `.cursor/rules/team-rules.mdc` | Pointers so Claude Code and Cursor load AGENTS.md. Codex reads AGENTS.md natively. |
| `.claude/settings.json` | Makes Claude Code print the context brief on every session start. |
| `scripts/context-brief.sh` | Prints STATE, CONTRACTS, open questions, decisions, newest logs. Run it in any tool. |
| `scripts/new-log.sh` / `new-log.ps1` | Create a log entry from the template (works without git). |
| `docs/agent-context/` | STATE, CONTRACTS, DECISIONS, OPEN_QUESTIONS, `log/`. The shared memory. |
| `docs/specs/` | FUNCTIONAL_SPEC, TECHNICAL_SPEC, TASKS. |
| `web/`, `server/`, `scoring/` | Code (frontend, backend, score config). |

## Why one log file per change
Two people appending to one file causes merge conflicts. New files never
conflict, and the filename (timestamp first) sorts into a timeline.

## Starting any agent session
- Claude Code: automatic (the hook runs the brief). Just state your name and task.
- Cursor / Codex / other: paste this.
> Run `bash scripts/context-brief.sh` (or read the files listed in AGENTS.md section 0), then follow
> AGENTS.md section 1. Reply with a 5-line summary of what the team is doing and what is in progress
> before you start. My name is <name>. My task: <task>.

## Ending / handing off any agent session
> Follow AGENTS.md sections 3 and 4: write the log entry (Next step and Open issues exact), update
> CONTRACTS.md / DECISIONS.md / OPEN_QUESTIONS.md if needed, update only my section of STATE.md,
> commit code and context together, then tell me the log path and the one-line next step.

## Giving the project to a new person
Send them the repo and say: "Run the start prompt above." Everything else is in the files.

## Human habits (the part agents cannot do)
- Split by folder so you rarely touch the same file (`web/` vs `server/`).
- Pull before every work block, push after every working step (every 30-45 min).
- Before a risky change, post one line in team chat; logs are for agents, chat is for surprises.
- Every 2-3 hours, read the newest log files for 2 minutes and update "Last full review" in STATE.md.
- Keep CONTRACTS.md truthful. Most bugs between two people come from a changed shape nobody told the other side about.

## Tool notes
- If a tool ignores the rules, paste the start prompt; the first message is what an agent reads first.
- Hooks only exist in Claude Code; other tools rely on the rules file plus the start prompt.
- Never put API keys in these files. Use `.env` (git-ignored); names go in `.env.example`.
