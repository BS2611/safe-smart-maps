# Running Safe Smart Maps on a phone

Safe Smart Maps is a web app (Next.js) that installs to the home screen like an app. It is **not** React Native,
and nothing needs compiling to run it on Android or iPhone. Decision: DECISIONS.md, 2026-10-24 12:05
("one responsive PWA, no native phone apps").

## A. Your own Android phone over USB (best: uses localhost, so the Mapbox token and location work)
You need Android Studio's `adb` (Platform-Tools). Usual path on Windows:
`C:\Users\<you>\AppData\Local\Android\Sdk\platform-tools\adb.exe` (Android Studio > Settings > Android SDK > SDK Tools > Android SDK Platform-Tools).

1. On the phone: Settings > About phone > tap **Build number** 7 times > Developer options > turn on **USB debugging**. Plug in the USB cable and accept the prompt.
2. Check it is seen: `adb devices` (should list your phone as `device`).
3. On the PC, start the backend and the web app (two terminals):
   ```bash
   .venv/Scripts/python -m uvicorn server.main:app --port 8000
   cd web && npm run dev          # http://localhost:3000
   ```
4. Forward the phone's `localhost` to the PC:
   ```bash
   adb reverse tcp:3000 tcp:3000
   adb reverse tcp:8000 tcp:8000
   ```
5. On the phone open **Chrome** and go to `http://localhost:3000`. It works like on the PC: the Mapbox token (restricted to localhost:3000) is accepted, "Use my location" works (localhost counts as secure), and the app reaches the backend on `localhost:8000`.
6. Chrome menu > **Add to Home screen** / **Install app** to test the installed (full screen) version.
7. Debug from the PC: open `chrome://inspect/#devices` in desktop Chrome and inspect the phone page.

Redo step 4 if you unplug the cable.

## B. Android emulator (no phone needed)
Android Studio > Device Manager > Create device (a Pixel with a Play Store image) > start it, then:
```bash
adb reverse tcp:3000 tcp:3000
adb reverse tcp:8000 tcp:8000
```
Open Chrome in the emulator at `http://localhost:3000`. In the emulator's "..." menu > Location you can set a position in San Francisco.

## C. Phone on the same Wi-Fi, no cable (limits)
`npm run dev -- -H 0.0.0.0`, allow port 3000 and 8000 in Windows Firewall, then open `http://<PC Wi-Fi IP>:3000` on the phone (find the IP with `ipconfig`).
Limits: the Mapbox token is restricted to localhost, so add that URL to the token's allowed URLs or the map stays blank; and because it is plain http, browsers block location and the install prompt. Prefer A or D.

## D. iPhone (and anything else): needs https
iPhone Safari only allows location and "Add to Home Screen" install features on **https**. Options:
- **Quick tunnel:** `npx cloudflared tunnel --url http://localhost:3000` (or ngrok) gives an https address. Add that address to the Mapbox browser token's allowed URLs, and set `WEB_ORIGINS` on the server and `NEXT_PUBLIC_API_BASE_URL` to a tunnel for port 8000 as well.
- **Deploy:** web on Vercel, backend on any small host (Render, Fly, Railway). Put the real domain in the Mapbox token's allowed URLs and in `WEB_ORIGINS`.
Then on the iPhone: open the address in Safari > Share > **Add to Home Screen**.

## E. Android app (APK) built from the same web app
Done with **Capacitor** (not React Native; nothing was rewritten). The Android project is `web/android`. Decision: DECISIONS.md, 2026-10-24 (Capacitor wrapper).

Build the web bundle and copy it into the Android project:
```bash
cd web
npm run build:android          # sample-data build: works with NO backend (saved sample routes, orange "Sample data" banner)
npm run build:android:live     # talks to the backend at NEXT_PUBLIC_API_BASE_URL (use your PC address or a hosted https URL, not localhost)
```
Then make the APK, in **Android Studio**:
1. Open the folder `web/android` (File > Open). Let it sync Gradle. The first time, accept the prompt to install the missing Android SDK pieces (SDK Platform 36 and Build-Tools); Studio downloads them.
2. Plug the phone in with USB debugging on (section A, step 1), or start an emulator.
3. Press the green **Run** button to install and open it on the phone, **or** Build > Build Bundle(s) / APK(s) > **Build APK(s)**. The file is `web/android/app/build/outputs/apk/debug/app-debug.apk`; copy it to the phone and open it (allow "install unknown apps" once).

Command line instead (needs the SDK installed and `ANDROID_HOME` set): `cd web/android && gradlew assembleDebug`.

Things to know:
- The app contains the browser Mapbox token from `web/.env.local`. That token is restricted by URL; the app runs from `https://localhost`, so add `https://localhost` to the token's allowed URLs or the map falls back to the simple route drawing.
- "Use my location" asks for the Android location permission.
- After changing any web code, run `npm run build:android` again before rebuilding the APK.
- The debug APK is for testing only. A release/Play Store build needs a signing key (not set up).
- iPhone: Capacitor can also make an iOS app, but that needs a Mac with Xcode. Not set up.

## What to check on a real phone
Welcome and Plan fit without sideways scrolling; keyboard does not hide "Show routes"; the map draws and pans; coverage/segment colors also show symbols; the install tip appears on iPhone; "Use my location" asks for permission and, if denied, shows "Location is off"; portrait and landscape.
