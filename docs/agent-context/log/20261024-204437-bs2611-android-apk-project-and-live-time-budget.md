# Android project (Capacitor), route page as query, time budgets and saved copies

- When: 2026-10-24 20:35 PT
- Who: Bhavpreet (agent: claude-code)
- Branch / commit: ui / see git log
- Files touched: web/android/** (generated Capacitor project; location permissions added to AndroidManifest.xml), web/capacitor.config.ts, web/scripts/build-android.mjs, web/next.config.mjs (static export when BUILD_TARGET=android), web/app/route/page.tsx + components/RouteDetailGate.tsx (replace app/routes/[routeId]), RouteCard link, web/app/manifest.ts, web/package.json (scripts, 3 Capacitor deps), docs/PHONE_TESTING.md; backend: server/data/places_cache.py (new), server/data/osm.py (saved copy), server/services/planner.py (time budgets, background lookups, shared in-flight jobs), server/wiring.py, tests/test_budgets_and_places_cache.py, tests in test_providers.py/test_planner.py, .env.example, .gitignore
- What changed: (1) APK path: the web app now exports as static files and Capacitor packs them into web/android. (2) Live-test finding: the 5.5 km demo trip needs 12 Bright Data lookups of 60-100 s each, so one request hung for over 9 minutes and Overpass (street data) was down. The planner now answers within about 40 s, reports "still loading", and finishes lookups in the background; listings and street data are saved to disk and shared between requests.
- Decisions made in chat (also added to DECISIONS.md? yes): Capacitor wrapper; time budgets and saved copies.
- Contracts affected: none (new warning texts only).
- How it was tested: backend pytest 285+ passed, ruff clean; vitest 202 passed; next build for web and for the Android export OK; Playwright 54 passed; `npx cap add android` and `cap sync` OK. NOT DONE: the APK itself was not built, because this PC has no Android SDK yet (Android Studio is installed but its SDK download has not run). Live Mapbox, Bright Data and Claude passed in `pytest -m live` earlier today; a full live trip was NOT completed (stopped for cost and Overpass being down).
- Unfinished / uncommitted: none after commit.
- Open issues / risks: Bright Data cost: each uncached area is a paid job (about 60 records x 3 keywords); a 5.5 km trip is about 12 areas. Prefer a short demo corridor and pre-warm once. The Mapbox browser token allows only localhost:3000 until https://localhost is added for the app. Android Gradle with Java 25 (Studio's bundled JDK) was not tried from the command line; build from Studio.
- Next step for whoever continues: open web/android in Android Studio, let it install the SDK, build the APK (docs/PHONE_TESTING.md section E). Then run one short live trip and pre-warm.
- Needs from teammate: Amey: backend readiness; confirm the Bright Data cost per lookup.
