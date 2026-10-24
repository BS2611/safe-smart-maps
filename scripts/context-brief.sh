#!/usr/bin/env bash
# Usage: bash scripts/context-brief.sh
# Prints the shared team context so any agent (or person) can start warm.
# Read-only. Claude Code runs this automatically at session start (.claude/settings.json).
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 0
ctx="docs/agent-context"
show() { echo; echo "=================== $1 ==================="; cat "$1" 2>/dev/null || echo "(missing)"; }

echo "SAFE SMART MAPS - TEAM CONTEXT BRIEF ($(date '+%Y-%m-%d %H:%M'))"
echo "Rules: AGENTS.md. Files win over chat memory. Reply to your human with a 5-line summary before editing."
if git rev-parse --git-dir >/dev/null 2>&1; then
  echo "git: branch $(git symbolic-ref --short -q HEAD 2>/dev/null || echo detached); run 'git pull --rebase' first."
  git status --short 2>/dev/null | head -20
else
  echo "git: NOT a git repo yet (say so to your human)."
fi

show "$ctx/STATE.md"
show "$ctx/CONTRACTS.md"
show "$ctx/OPEN_QUESTIONS.md"
echo; echo "=================== $ctx/DECISIONS.md (last 15 lines) ==================="
tail -n 15 "$ctx/DECISIONS.md" 2>/dev/null

echo; echo "=================== 10 NEWEST LOG ENTRIES (oldest first) ==================="
ls "$ctx"/log/2*.md 2>/dev/null | sort | tail -n 10 | while read -r f; do
  echo; echo "----- $f -----"; cat "$f"
done
echo; echo "Specs: docs/specs/ (FUNCTIONAL_SPEC, TECHNICAL_SPEC, TASKS). Finish with scripts/new-log.sh."
