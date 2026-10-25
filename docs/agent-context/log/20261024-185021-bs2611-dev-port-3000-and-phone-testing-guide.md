# Dev port 3000, CORS test fix, phone testing guide

- When: 2026-10-24 19:05 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: ui / see git log
- Files touched: docs/PHONE_TESTING.md (new), README.md, .env.example, web/package.json (dev/start port 3000), server/main.py (allowed_origins helper, default origin 3000; Amey's file), tests/test_api_routes.py, web/playwright.config.ts (comment). Local .env (git-ignored): WEB_ORIGINS set to http://localhost:3000.
- What changed: The web app now defaults to port 3000 everywhere, because the Mapbox browser token is restricted to localhost:3000. CORS origin parsing is a tested function; the CORS test no longer depends on whatever WEB_ORIGINS is in a developer's .env (it failed on this machine when .env said 3100). New guide for running on Android (USB with adb reverse, emulator), iPhone (https needed) and an optional Capacitor wrapper.
- Decisions made in chat (also added to DECISIONS.md? no): the app stays a web app/PWA; React Native is not used (same as the 12:05 decision).
- Contracts affected: none.
- How it was tested: pytest 272 passed, ruff clean, secrets OK. Phone steps are not run (adb not found at the default SDK path; no device attached from here).
- Unfinished / uncommitted: none after commit.
- Open issues / risks: running servers started earlier on 3100 or 3000 need a restart to pick up the new port settings; backend must be restarted to read .env.
- Next step for whoever continues: follow docs/PHONE_TESTING.md section A on a real Android phone.
- Needs from teammate: none
