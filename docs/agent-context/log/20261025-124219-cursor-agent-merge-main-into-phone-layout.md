# merge main into phone layout

- When: 2026-10-25 05:42 PT
- Who: Cursor Agent (agent: cursor)
- Branch / commit: cursor/mobile-fixes-01d5 / uncommitted
- Files touched: docs/agent-context/DECISIONS.md, docs/agent-context/STATE.md, and the street-view files brought in from main
- What changed: Merged main (after street view, PR #12) into the phone-layout branch. Kept both the phone-grid decision and the street-view decision. Kept main's street-view code. The phone grid, sticky plan hint, and launcher icons stay.
- Why: PR #13 conflicted with main once street view merged.
- Decisions made in chat (also added to DECISIONS.md? no new decision): kept both existing lines
- Contracts affected: none beyond what main already added for street view
- How it was tested: `npm test` 235 passed. `npm run lint` clean. `npx tsc --noEmit` clean. `NEXT_DIST_DIR=.next-e2e-mobile npx playwright test --project=android-chromium --project=small-android-360` passed 38 tests, including the phone-width checks. WebKit was not launched.
- Unfinished / uncommitted: none of this merge. docs/hackathon is not part of this branch.
- Open issues / risks: STATE "Last full review by a human" is still blank.
- Next step for whoever continues: Review pull request #13.
- Needs from teammate: none
