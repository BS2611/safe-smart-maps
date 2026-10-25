# night route logo

- When: 2026-10-25 03:06 PT
- Who: owner via cursor (agent: cursor)
- Branch / commit: cursor/night-mark-01d5 / this commit
- Files touched: web/components/Icons.tsx, web/app/polish.css, web/app/layout.tsx, web/public/icons/logo.svg, web/public/icons/icon-192.png, web/public/icons/icon-512.png, web/public/icons/icon-maskable-512.png, web/public/icons/apple-touch-icon.png, web/app/favicon.ico, docs/agent-context/DECISIONS.md
- What changed: Replaced the header mark and the app icons with one night-route drawing: a walk that turns a corner, coral at the start, amber at the turn, a mint glow at the lit point, on #07110e. The wordmark is still "Safe Smart Maps".
- Why: The owner asked for a distinctive logo that matches the night-map and score colors and still reads at favicon size.
- Decisions made in chat (also added to DECISIONS.md? yes): The mark above is the logo. No Open Graph image existed, so none was added. Android launcher mipmaps are still the Capacitor placeholder, not this mark, so they were left alone.
- Contracts affected: none
- How it was tested: npm test (206 passed), npm run lint (clean), npm run typecheck (clean), and NEXT_DIST_DIR=.next-e2e npx playwright test --project=android-chromium --project=small-android-360 (production build, then 36 passed). Opened http://localhost:3000/ in Chrome on the desktop and saw the new mark next to Safe Smart Maps. favicon.ico, logo.svg, icon-192, and apple-touch-icon all returned 200.
- Unfinished / uncommitted: docs/hackathon/ is untracked and was not touched. web/tsconfig.json was restored after the production build so the .next-e2e type path is not committed.
- Open issues / risks: STATE.md "Last full review by a human" is still blank. WebKit e2e was not run here (Chromium only). There is no Open Graph image in the app.
- Next step for whoever continues: Review the new pull request. If the Android home-screen icon should match, regenerate web/android mipmap icons from web/public/icons/logo.svg.
- Needs from teammate: none
