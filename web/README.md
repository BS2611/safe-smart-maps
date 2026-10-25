# web/ - Safe Smart Maps app (Next.js)

The phone-first UI: Welcome, Plan trip, Preferences, Checking, Routes (map + three route cards), Route details,
8 PM vs 1 AM compare, How scores work. It talks to the backend only through `POST /v1/routes`
(contract: `docs/agent-context/CONTRACTS.md`). It does not contain scoring logic.

## Run
```bash
cd web
npm install
cp .env.example .env.local      # then fill in the values you have
npm run dev                     # http://localhost:3000
```
- With the backend running (`uvicorn server.main:app --port 8000`) the app uses it (`NEXT_PUBLIC_API_BASE_URL`).
- No backend yet? Set `NEXT_PUBLIC_DEV_FIXTURES=1` in `.env.local`: the screens run on saved sample routes under an
  orange "Sample data" banner. Off by default.

### Local and Render/demo profiles

Keep two ignored files so the UI can talk to either backend without editing URLs:

```bash
cp .env.example .env.local
cp .env.demo.example .env.demo
npm run dev:local  # local UI :3000 -> local backend :8000
npm run dev:demo   # demo UI :3001 -> https://safe-smart-maps.onrender.com
```

Fill the same URL-restricted `NEXT_PUBLIC_MAPBOX_TOKEN` into both files. Its allowed URLs must include
`http://localhost:3000` and `http://localhost:3001`; add the deployed frontend URL when the production UI exists.

## Test (all must pass before a merge)
```bash
npm run lint && npm run typecheck && npm run test:coverage     # unit tests, coverage gate 80%
npm run e2e                                                    # builds, then iPhone WebKit, Android Chromium, 360 px, incl. accessibility
```
The tests read saved backend responses from `../tests/fixtures/routes_response*.json` (labeled fixtures). If the backend
response shape changes, regenerate them and run the tests: `routes_response_main_backend.json` is a real response from main's
planner and proves the UI accepts main's shape.

## Android app (APK)
Capacitor wraps this same app; project in `web/android`. One command on Windows (Git Bash): `bash web/scripts/build-apk.sh`
(needs the Android SDK in `~/Android/Sdk` and JDK 17-21 in `~/Android/jdk/`). Details: `docs/PHONE_TESTING.md`.

## Rules the UI follows
Never says a route is "safe" (automated test scans all UI text); "not sure" for missing data; every band has a symbol, not only
a color; weights and thresholds shown must equal `scoring/scoring_v1.json` (tested).
