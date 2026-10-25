# watch check-in and android inset

- When: 2026-10-25 07:46 PT
- Who: owner via cursor (agent: cursor)
- Branch / commit: cursor/watch-checkin-01d5 / this commit
- Files touched: web/lib/trip.ts, web/lib/nav/checkin.ts, web/components/PreferencesScreen.tsx, web/components/NavigationScreen.tsx, web/components/RouteDetailScreen.tsx, web/app/globals.css, web/app/polish.css, tests for those, web/e2e/flow.spec.ts, docs/specs/FUNCTIONAL_SPEC.md, docs/agent-context/DECISIONS.md, docs/agent-context/STATE.md
- What changed: Route preferences gained a Watch check-in toggle (default off) stored with the other trip settings and left out of POST /v1/routes. During walking navigation, when it is on, a check-in opens every 3 minutes and once per visit to the darkest known stretch, the phone buzzes, and I'm OK dismisses it. `pingPairedWatch` returns unavailable and adds no native plugin. Narrow screens reserve at least 48px plus the safe-area inset under the route detail actions, the plan bar, the nav dock, and the page.
- Why: The owner asked for a watch check-in on the walk, and the route detail Start button sat on the bottom edge of a tall Android screen.
- Decisions made in chat (also added to DECISIONS.md? yes): check-in stays client-only; no Capacitor wearable dependency; 3 minute interval; darkest prompt once per visit until the walker leaves; 48px floor on viewports at most 840px wide.
- Contracts affected: none. The route request body is unchanged.
- How it was tested: `npm run test:coverage` 298 passed, branches 82.41%. `npm run lint` and `npx tsc --noEmit` clean. Playwright Chromium Pixel 7 and 360x640: 40 passed, including Start clearance and the saved check-in preference. WebKit was not launched (missing system libraries). `BUILD_TARGET=android NEXT_DIST_DIR=.next-android npx next build` wrote the static site into `.next-android` (not `out`); the same env `npx cap sync android` copied that folder. Export strings for the merged UI, copy, logo, scores, street view, and walking nav are present. Gradle files stayed LF. No Android SDK, so `gradlew assembleDebug` was not run. A browser pass turned check-in on, saw space under Start, simulated the walk, got the darkest-stretch check-in, and cleared it with I'm OK.
- Unfinished / uncommitted: none in this commit. `docs/hackathon/` and `.next-android/` stay untracked.
- Open issues / risks: STATE "Last full review by a human" is still blank. The paired watch is not actually pinged. On a desktop wider than 840px the 48px floor does not apply. A WebView older than the Capacitor safe-area fix already pads natively, so the CSS floor can add extra space.
- Next step for whoever continues: Review the pull request. A phone APK still needs an Android SDK (`gradlew assembleDebug` in web/android) after `BUILD_TARGET=android NEXT_DIST_DIR=.next-android` on both `next build` and `cap sync`.
- Needs from teammate: none. Do not edit server/ or watch/ for this preference.
