# bolder screen polish

- When: 2026-10-25 00:49 PT
- Who: owner request (agent: cursor)
- Branch / commit: cursor/ui-polish-01d5 / this commit
- Files touched: web/app/polish.css, web/components/RouteIllustration.tsx, docs/agent-context/DECISIONS.md
- What changed: Richer night palette, larger type, more space between blocks, glowing score rings, and transform-only motion on cards, buttons, the route list, detail, comparison, plan, preferences, how-scores, and the checking screen. Landing headline and night-map frame are larger. No login screen was added.
- Why: Owner asked for the most striking polish on every existing screen, including login if it already existed.
- Decisions made in chat (also added to DECISIONS.md? yes): no auth page exists, so none was built. STATE.md was not edited.
- Contracts affected: none
- How it was tested: `npm test` 206 passed; `npm run lint` clean; `npm run typecheck` clean. `NEXT_DIST_DIR=.next-e2e npx playwright test --project=android-chromium --project=small-android-360` built the app and passed 36 tests, including color contrast. WebKit was not launched here.
- Unfinished / uncommitted: web/package-lock.json and docs/hackathon/ were left unstaged. web/tsconfig.json was restored after the e2e build rewrote it.
- Open issues / risks: STATE "Last full review by a human" is still blank.
- Next step for whoever continues: reload http://localhost:3000/ and walk landing, plan, routes, a route detail, and 8 PM vs 1 AM. CI should run the WebKit project.
- Needs from teammate: none
