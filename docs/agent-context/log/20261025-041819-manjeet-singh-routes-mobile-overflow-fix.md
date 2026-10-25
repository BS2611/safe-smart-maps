# routes-mobile-overflow-fix

- When: 2026-10-25 04:18
- Who: Manjeet Singh (agent: GitHub Copilot)
- Branch / commit: manjeetsingh-satveer-mobile-ui-refresh on top of main 268ed17 (PR #9) / uncommitted
- Files touched: web/app/polish.css
- What changed: The shared page grids (.plan-layout, .routes-layout, .detail-layout, .guide-grid, .compare-top) now use `grid-template-columns: minmax(0, 1fr)`, and their children get `min-width: 0`. On phones the routes screen no longer runs past the right edge (map, legend, "fetched" row were cut off).
- Why: A grid column with no set width grew to fit the widest child (the route drawing/map), so the page was wider than the phone.
- Decisions made in chat (also added to DECISIONS.md? yes/no): none new. The phone app (Capacitor APK) uses the Render backend (NEXT_PUBLIC_API_BASE_URL=https://safe-smart-maps.onrender.com in git-ignored web/.env.local). Manjeet added https://localhost to WEB_ORIGINS on Render so the Android app (origin https://localhost) can call /v1/routes.
- Contracts affected: none
- How it was tested: Built the live Android bundle (BUILD_TARGET=android, NEXT_DIST_DIR=.next-android, copied to web/out), ran `npx cap sync android` and `gradlew assembleDebug` (exit 0), then `adb install -r` on the Samsung S22 Ultra. Planned Palace of Fine Arts -> Montgomery BART: the routes screen fits the width, the Mapbox map loads, and live routes come back from Render. Unit tests not run (CSS-only change).
- Unfinished / uncommitted: web/app/polish.css and this log are uncommitted. web/android/app/capacitor.build.gradle and web/android/capacitor.settings.gradle show only line-ending changes from `cap sync`.
- Open issues / risks: The Android launcher icons in web/android/app/src/main/res were not updated by PR #9 (home-screen icon is still the old one). The plan screen's hint text ("Live data covers the demo area...") shows through behind the sticky "Show routes" button on the phone.
- Next step for whoever continues: Review and commit web/app/polish.css. To rebuild the phone app: in web/, build with BUILD_TARGET=android and NEXT_DIST_DIR=.next-android, copy .next-android to out, run `npx cap sync android`, then in web/android run `gradlew assembleDebug` with ANDROID_HOME=%USERPROFILE%\Android\Sdk and TEMP=C:\tmp, then `adb install -r app\build\outputs\apk\debug\app-debug.apk`.
- Needs from teammate: none
