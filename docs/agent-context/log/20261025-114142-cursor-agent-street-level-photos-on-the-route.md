# street-level photos on the route

- When: 2026-10-25 04:41 PT
- Who: owner via cursor (agent: cursor)
- Branch / commit: cursor/street-view-01d5 / this commit
- Files touched: web/components/StreetView.tsx, Pegman.tsx, RouteDetailScreen.tsx, RouteMap.tsx, SegmentMap.tsx, web/lib/streetview/*, web/lib/geometry.ts, web/app/polish.css, web/package.json, web/package-lock.json, README.md, .env.example, docs/agent-context/CONTRACTS.md, DECISIONS.md, STATE.md, docs/specs/FUNCTIONAL_SPEC.md
- What changed: Route detail can open a street-level photo by tapping the map, dragging a peg, or previewing the darkest stretch. The viewer looks around, steps along the route, and shows a mini map plus that stretch's score and reasons. Mapillary is the provider. Google Street View is used only when its browser key is set. No key shows "Street view is unavailable."
- Why: Owner asked for a Google-Maps-style street view on the route map, with a free provider because this repo has no Google Maps key.
- Decisions made in chat (also added to DECISIONS.md? yes): Mapillary via mapillary-js and NEXT_PUBLIC_MAPILLARY_TOKEN. Optional swap is NEXT_PUBLIC_GOOGLE_MAPS_API_KEY. Recorded in DECISIONS.md 2026-10-25 04:41.
- Contracts affected: CONTRACTS.md Config and env, two new browser env names. Route JSON is unchanged.
- How it was tested: In web/, `npm run test:coverage` (235 passed; statements 92.61%, branches 82.37%, functions 94.72%, lines 95.03%). `npm run lint` clean. `npm run typecheck` clean. `NEXT_DIST_DIR=.next-e2e npm run build` succeeded. `NEXT_DIST_DIR=.next-e2e npx playwright test --project=android-chromium --project=small-android-360` 36 passed. WebKit was not run. No Mapillary token was present, so the browser checks covered the unavailable state and the existing demo, not a live panorama.
- Unfinished / uncommitted: none in this commit. docs/hackathon/ stays untracked. No key was committed.
- Open issues / risks: STATE "Last full review by a human" is still blank. A live panorama needs NEXT_PUBLIC_MAPILLARY_TOKEN in web/.env.local (Mapillary client token). Without it the screen says street view is unavailable. Mapillary drag-to-look is the viewer's own pointer control; the mini map heading follows that bearing once a photo loads.
- Next step for whoever continues: Add NEXT_PUBLIC_MAPILLARY_TOKEN to web/.env.local, open a route, tap the map, and confirm a photo loads, the arrows step along the walk, and Close returns to the map.
- Needs from teammate: none
