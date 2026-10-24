# AGENTS.md - rules for every AI agent in this repo

Applies to Claude Code, Cursor, Codex, and any other agent or human newcomer.
Two humans share this repo (see docs/agent-context/STATE.md for names) plus a
guide. You will NOT have anyone's chat history. **If it is not written in a
file in this repo, it does not exist for the next agent.** The files in
docs/agent-context/ ARE the shared memory. Treat them as the source of truth,
not your own assumptions or an earlier chat.

Project: Safe Smart Maps (Cal Hacks 13.0). Walking routes scored by lighting,
open places at arrival time, main roads, help points, transit, activity
estimate, and a continuity rule. Data: Bright Data (core live feed), Apify
(supporting), Mapbox (map and routing), Claude API (explanations).
Deadline: Sunday 9:00 AM PT (Devpost submission).

## 0. Where things live
| Need | File |
|---|---|
| Who owns what, what is in progress | docs/agent-context/STATE.md |
| Data shapes, endpoints, env names, folder layout | docs/agent-context/CONTRACTS.md |
| Choices already made (append only) | docs/agent-context/DECISIONS.md |
| Questions nobody has answered yet | docs/agent-context/OPEN_QUESTIONS.md |
| History of every change, newest last | docs/agent-context/log/ |
| What the product does | docs/specs/FUNCTIONAL_SPEC.md |
| How it is built, algorithms | docs/specs/TECHNICAL_SPEC.md |
| Task list and milestones | docs/specs/TASKS.md |
Precedence when files disagree: CONTRACTS.md > DECISIONS.md > specs > chat.

## 1. Before you change anything (every session, no exceptions)
1. Run `bash scripts/context-brief.sh`. It prints STATE, CONTRACTS, open
   questions, recent decisions and the newest log entries in one go (Claude
   Code runs it automatically on session start; other tools must run it).
2. If this is a git repo, run `git pull --rebase` first. If it is not a git
   repo yet, say so in your first reply and continue (files still carry context).
3. Read anything the brief truncated that relates to your task (full log
   entries, the relevant spec section).
4. Reply to your human with a 5-line summary: what the team is doing, what is
   in progress, what you will do, which files you will touch, anything stale
   or contradictory. Wait for a go-ahead if anything is contradictory.
5. If the task touches a file the other person owns or has "in progress" in
   STATE.md, STOP and tell your human before editing.
6. If STATE.md "Last full review by a human" is blank or older than ~3 hours,
   say so; ask your human to confirm STATE is still true.

## 2. While you work (do not wait until the end)
- Anything decided in chat (a choice, a name, a number, "we agreed to...")
  goes into DECISIONS.md or OPEN_QUESTIONS.md **at that moment**.
- Checkpoint: write a log entry after every meaningful step, at least every
  30-45 minutes, and before any long or risky operation. Agents can be cut off
  without warning; an unwritten step is a lost step.
- Fill "Files in progress" in your human's STATE section when you start
  editing, clear it when done.

## 3. After every meaningful change (before you say "done")
1. Create a log entry: `scripts/new-log.sh "short-title"` (Windows PowerShell:
   `scripts/new-log.ps1 "short-title"`). Fill in EVERY field, including
   "Decisions made in chat" and "Unfinished / uncommitted". One file per
   change. Never edit or delete old log files (add a new one to correct).
2. If you changed a shared format, API, env var, or file layout: update
   `CONTRACTS.md` in the same commit, and say so in the log entry.
3. If you made a design choice others must respect: add a line to
   `DECISIONS.md` (date, who, decision, reason). Remove the matching row from
   OPEN_QUESTIONS.md.
4. Update only YOUR human's section of `STATE.md` (status, doing now, files in
   progress, next, blocked on). Never edit the other person's section.
5. If a spec is now wrong, fix the spec or note the mismatch in the log.
6. Commit the code and the context files together (when git exists).

## 4. Handoff protocol (switching agent, tool, person, or ending a session)
Do this whenever you stop, hit a limit, switch tools, or the human says
"transfer", "hand off", or "I'm done":
1. Write the log entry with **Next step** and **Open issues** filled in
   concretely (file names, commands, the exact next action). Write it so an
   agent with zero memory can continue cold.
2. Update STATE.md (your human's section).
3. List in the log anything you know that is not in a file yet.
4. Tell the human, in the final message: where the log is, and the one-line
   next step.
The receiving agent: follow section 1, then restate the handoff ("Last agent
did X, next is Y") to the human before touching files. If the log and the code
disagree, trust the code, then write a log entry saying what was wrong.

## 5. Git rules
- Work on a branch named `<person>/<topic>` (example: `bhav/route-scoring`).
  Never commit straight to `main`.
- Small commits, clear messages. `git pull --rebase` before you push.
- Never force-push. Never rewrite shared history. Never delete branches you
  did not create.
- If a merge conflict appears, do not guess. Show both sides to your human.
- Context files (docs/agent-context/) are committed with the code, never left
  out.

## 6. Do not break these (project rules)
- No secrets in the repo. Keys live in `.env` (git-ignored). Add new
  variable names to `.env.example` with no values.
- Bright Data path: real live data only. No mocked or hardcoded business
  data in the core flow. Test fixtures go in `tests/fixtures/` and must be
  labeled. Public pages only, nothing behind a login or paywall.
- Never describe a route as "safe". Use "better lit and more active", and
  always show the reasons and the data time.
- Missing or old data must show as "not sure", never a guessed value.
- Heart-rate or location data: opt-in, minimal, not stored after the trip.
  Simulated readings must be labeled "simulated" in the UI and code.
- Do not add a new paid service or dependency without writing it in
  DECISIONS.md and telling your human.

## 7. Working style
- Smallest change that solves the task. Do not refactor files you were not
  asked to touch.
- Keep the score config versioned (`scoring/scoring_v1.json`) and each data
  source behind its own module, so parts can be swapped later.
- If the task is unclear or conflicts with CONTRACTS.md or DECISIONS.md, ask
  your human instead of guessing.
- Never claim something works unless you ran it. Say what you ran and what
  you saw. If you could not test, say so in the log entry.
- Write plainly; no jargon the other person would have to look up.

## Git attribution
- Never add AI agents as commit authors or co-authors.
- Do not add `Co-Authored-By` lines for Claude, Codex, Cursor, Anthropic, OpenAI, or any other AI tool.
- Do not add AI-generated attribution, signatures, or promotional links to commit messages or pull requests.
- Git commits must use the human developer's configured `git user.name` and `git user.email`.