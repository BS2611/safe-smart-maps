# frontend-backend-env-profiles

- When: 2026-10-24 22:19 PT
- Who: bs2611 / Codex
- Branch / commit: main / uncommitted
- Files touched: `web/.env.demo.example`, `web/scripts/start-profile.mjs`, `web/package.json`, `web/README.md`, `.gitignore`, this log
- What changed: Added separate local and demo frontend profiles. `npm run dev:local` uses `http://localhost:8000` on port 3000; `npm run dev:demo` uses `https://safe-smart-maps.onrender.com` on port 3001. The demo template contains no token value and the copied `.env.demo` remains ignored.
- Why: Local-backend and Render-backend testing can run independently without repeatedly changing API URLs.
- Decisions made in chat (also added to DECISIONS.md? yes/no): Use Render as the demo backend; keep local and demo frontend environment files separate; use ports 3000 and 3001; no new dependency added. No DECISIONS.md change needed.
- Contracts affected: None; `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_MAPBOX_TOKEN` names are unchanged.
- How it was tested: `node --check web/scripts/start-profile.mjs` passed. `npm run typecheck --prefix web` could not run because the installed npm launcher points to a missing `npm-cli.js`; no typecheck result is available.
- Unfinished / uncommitted: Changes are not committed yet. User must copy `web/.env.demo.example` to `web/.env.demo` and place the URL-restricted Mapbox browser token in both profiles. Existing `.cursor/settings.json` and prior context-file edits remain unrelated/uncommitted.
- Open issues / risks: Mapbox browser token allowed URLs must include `http://localhost:3000` and `http://localhost:3001`, plus any deployed frontend URL. `web/.env.demo` must not be committed.
- Next step for whoever continues: From `web/`, run `Copy-Item .env.demo.example .env.demo`, fill the token, then run `npm run dev:local` and `npm run dev:demo` in separate terminals; verify each UI reaches its intended backend.
- Needs from teammate: Confirm the Mapbox token restriction includes port 3001 and the deployed frontend origin.
