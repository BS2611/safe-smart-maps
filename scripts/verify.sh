#!/usr/bin/env bash
# Full regression gate: everything CI runs, in one command. Run before every merge and at the end of
# every sprint (docs/specs/AGILE_PLAN.md, Definition of Done).
#
#   bash scripts/verify.sh           everything, including browser tests (about 3 minutes)
#   bash scripts/verify.sh --quick   skips the browser tests
#
# The live checks (real Bright Data, Mapbox, Claude) are separate: pytest -m live
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PY=".venv/Scripts/python"
[ -x "$PY" ] || PY=".venv/bin/python"
[ -x "$PY" ] || PY="python"
failures=()

step() {
  local name="$1"; shift
  echo; echo "=== $name ==="
  if "$@"; then echo "--- $name: OK"; else echo "--- $name: FAILED"; failures+=("$name"); fi
}

step "secrets check"       bash scripts/check-secrets.sh
step "backend lint (ruff)" "$PY" -m ruff check .
step "backend tests"       "$PY" -m pytest --cov -q
(cd web && npm run lint --silent) >/dev/null 2>&1 && echo "web lint ok" || { echo "web lint FAILED"; failures+=("web lint"); }
step "web type-check"      bash -c "cd web && npm run typecheck --silent"
step "web unit tests"      bash -c "cd web && npm run test:coverage --silent"
if [ "${1:-}" != "--quick" ]; then
  step "web build + browser tests (iPhone WebKit, Android Chromium, 360 px)" bash -c "cd web && npm run e2e --silent"
fi

echo
if [ "${#failures[@]}" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
  exit 0
fi
echo "FAILED: ${failures[*]}"
exit 1
