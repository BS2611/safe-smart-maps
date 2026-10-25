# Map CSS loaded statically (real Mapbox map now renders)

- When: 2026-10-24 18:50 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: ui / see git log
- Files touched: web/components/RouteMap.tsx
- What changed: mapbox-gl.css is now imported at the top of RouteMap.tsx instead of lazily inside the effect.
- Why: With a real browser token the map area was grey (console: "missing CSS declarations for Mapbox GL JS"). First live look at the real map found it. Unit tests mock the map library so they could not catch it.
- Decisions made in chat (also added to DECISIONS.md? no): none
- Contracts affected: none
- How it was tested: viewed at http://localhost:3000/routes with the real browser token: map tiles and the colored segments now draw. verify --quick green.
- Unfinished / uncommitted: none
- Open issues / risks: sample-data geometry is invented, so its lines do not follow real streets; live Mapbox routes will. The browser token only works from localhost:3000 (its URL restriction); port 3100 shows the drawing fallback or errors.
- Next step for whoever continues: run the backend (uvicorn server.main:app --port 8000), set NEXT_PUBLIC_DEV_FIXTURES=0 in web/.env.local, and check a live route.
- Needs from teammate: none
