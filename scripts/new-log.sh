#!/usr/bin/env bash
# Usage: scripts/new-log.sh "short title"
# Creates docs/agent-context/log/<timestamp>-<person>-<slug>.md from the template.
# Works with or without git.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
title="${1:-change}"
name="$(git config user.name 2>/dev/null || true)"
name="${name:-${USER:-${USERNAME:-unknown}}}"
person="$(echo "$name" | tr 'A-Z ' 'a-z-' | tr -cd 'a-z0-9-')"
person="${person:-unknown}"
slug="$(echo "$title" | tr 'A-Z ' 'a-z-' | tr -cd 'a-z0-9-' | cut -c1-40)"
ts="$(date +%Y%m%d-%H%M%S)"
file="docs/agent-context/log/${ts}-${person}-${slug}.md"
branch="$(git symbolic-ref --short -q HEAD 2>/dev/null || echo no-git)"
sed -e "1s/.*/# ${title}/" \
    -e "s/<YYYY-MM-DD HH:MM PT>/$(date '+%Y-%m-%d %H:%M')/" \
    -e "s#<branch> / <short hash>#${branch} / uncommitted#" \
    docs/agent-context/log/_TEMPLATE.md > "$file"
echo "$file"
echo "Now open it and fill in every field."
