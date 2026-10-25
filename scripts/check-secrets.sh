#!/usr/bin/env bash
# Fails if a secret-looking value or an env file is tracked by git.
# Usage: bash scripts/check-secrets.sh   (run by CI; also run before submission)
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
status=0

# 1. No env files except .env.example may be tracked.
bad_env="$(git ls-files | grep -E '(^|/)\.env($|\.)' | grep -v '\.env\.example$' || true)"
if [ -n "$bad_env" ]; then
  echo "FAIL: env files are tracked:"; echo "$bad_env"; status=1
fi

# 2. .env.example must hold names only (URLs and the cache TTL are allowed values).
leaky="$(grep -nE '^[A-Z_]+=.+' .env.example | grep -vE '^[0-9]+:(NEXT_PUBLIC_API_BASE_URL|CACHE_TTL_SECONDS|WEB_ORIGINS)=' || true)"
if [ -n "$leaky" ]; then
  echo "FAIL: .env.example has values:"; echo "$leaky"; status=1
fi

# 3. No key-shaped strings in tracked files (this script excluded).
pattern='sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|(pk|sk)\.eyJ[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|apify_api_[A-Za-z0-9]{20,}'
hits="$(git grep -nIE "$pattern" -- . ':!scripts/check-secrets.sh' || true)"
if [ -n "$hits" ]; then
  echo "FAIL: secret-looking strings found:"; echo "$hits" | sed -E 's/(.{60}).*/\1.../'; status=1
fi

[ "$status" -eq 0 ] && echo "OK: no secrets found."
exit "$status"
