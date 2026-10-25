# phone layout and launcher icon

- When: 2026-10-25 04:54 PT
- Who: owner (agent: cursor)
- Branch / commit: cursor/mobile-fixes-01d5 / d9b4745
- Files touched: web/app/polish.css, web/app/globals.css, web/components/PlanTripScreen.tsx, web/e2e/flow.spec.ts, web/android/app/src/main/res/mipmap-* (launcher, round, foreground), web/android/app/src/main/res/values/ic_launcher_background.xml, docs/agent-context/DECISIONS.md, docs/agent-context/STATE.md
- What changed: Phone grids use one `minmax(0, 1fr)` column and `min-width: 0` on the children so the route map cannot widen the page. The plan hint sits inside the sticky Show routes bar, and that bar is an opaque page color, so the hint does not show through the button. Android launcher, round, and adaptive foreground icons are the night-route mark from web/public/icons/logo.svg, on plate #07110e.
- Why: Copilot's uncommitted phone overflow fix, the plan hint showing through the sticky button, and the launcher icons still being the Capacitor placeholder.
- Decisions made in chat (also added to DECISIONS.md? yes): 2026-10-25 04:54 PT, phone column, opaque plan bar, launcher icons.
- Contracts affected: none
- How it was tested: `npm run test:coverage` 206 passed (statements 97.25%, branches 87.56%, functions 96.92%, lines 98.71%). `npm run lint` and `npm run typecheck` passed. `NEXT_DIST_DIR=.next-e2e npm run build` succeeded. Playwright Chromium `android-chromium` (Pixel 7) and `small-android-360` (360×640): 38 passed, including a loaded trip on plan, routes, detail, and compare with no sideways scroll. WebKit was not run. Measured the plan hint against the Show routes button at both widths (rest, scrolled, and page bottom): 10px gap, no overlap, sticky background `rgb(6, 17, 14)` with no gradient.
- Unfinished / uncommitted: docs/hackathon/ left untracked. web/tsconfig.json Next rewrite was restored and is not part of this commit. No gradle files changed.
- Open issues / risks: STATE "Last full review by a human" is still blank. Bhavpreet and Amey sections were not edited. Street view remains on PR #12 and is not in this branch.
- Next step for whoever continues: review the phone screens and the launcher icons on a device, then merge this PR separately from street view.
- Needs from teammate: none
