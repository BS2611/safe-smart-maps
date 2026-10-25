# clearer copy

- When: 2026-10-25 02:46 PT
- Who: owner request (agent: cursor)
- Branch / commit: cursor/clearer-copy-01d5 / this commit
- Files touched: web/components/DepartureField.tsx, WelcomeScreen, PlanTripScreen, CheckingScreen, RoutesScreen, RouteDetailScreen, RouteCard, CompareScreen, PreferencesScreen, HowScoresScreen, web/lib/api.ts, sources.ts, scoring-info.ts, trip.ts, matching tests, docs/agent-context/DECISIONS.md
- What changed: Departure is labeled Heading out, with chips Now, 8 PM, 1 AM, and Custom, and one helper line. Other screen copy was shortened. Behavior and the honesty notice are unchanged. Branched from latest main and kept the unmerged leave-time commit.
- Why: The owner disliked the long leave-time wording and asked for a copy pass on every screen.
- Decisions made in chat (also added to DECISIONS.md? yes): chip names and the one-line helper. STATE.md was not edited. docs/hackathon was not touched.
- Contracts affected: none
- How it was tested: `npm test` 206 passed; `npm run lint` clean; `npm run typecheck` clean. `NEXT_DIST_DIR=.next-e2e npx playwright test --project=android-chromium --project=small-android-360` built the app and passed 36 tests.
- Unfinished / uncommitted: web/package-lock.json and docs/hackathon/ were left unstaged.
- Open issues / risks: STATE "Last full review by a human" is still blank. docs/hackathon/DEMO.md may still say "Tonight 8 PM".
- Next step for whoever continues: open the new pull request against main and read the plan page chips.
- Needs from teammate: none
