# Safe Maps - Galaxy Watch app (Wear OS)

Small companion app for a Samsung Galaxy Watch 4 or newer. It reads heart rate during a walk, sends it to
the backend relay, shows "Are you OK?" when the rate looks unusual, and sends a (demo) alert if nobody answers.
Contract: `docs/agent-context/CONTRACTS.md` section "Watch relay endpoints". Heart rate is used during the walk
only and is never saved on the watch.

## What is in here
| File | Job | Unit tested |
|---|---|---|
| `TriggerDetector.kt` | baseline + sustained rise + second sign (sudden stop or very fast pace) | yes |
| `WalkController.kt` | sends readings, prompt, 30 s countdown, alert, "I'm OK" | yes |
| `Relay.kt` | HTTP calls to the relay, pairing result handling | yes |
| `HeartRateService.kt` | Health Services walking exercise in a foreground service (works with the screen off) | on the watch |
| `MainActivity.kt` | code pad, walking, prompt, alert screens | on the watch |

## Build the APK
Needs Android Studio (or the Android SDK + JDK 17-21). Open the `watch/` folder in Android Studio and press
Run, or from a terminal:

```bash
cd watch
./gradlew :app:testDebugUnitTest          # unit tests
./gradlew :app:assembleDebug              # APK in app/build/outputs/apk/debug/
# talking to a laptop on your Wi-Fi instead of Render:
./gradlew :app:assembleDebug -PrelayUrl=http://192.168.1.20:8000
```
The default backend is `https://safe-smart-maps.onrender.com` (`gradle.properties`, key `relayUrl`).
`watch/local.properties` (SDK path) is git-ignored; Android Studio creates it for you.

## Put it on your Galaxy Watch
1. Watch: Settings > About watch > Software information > tap **Software version** 7 times (Developer mode).
2. Watch: Settings > Developer options > turn on **ADB debugging** and **Wireless debugging**.
3. Watch and laptop on the same Wi-Fi. In Wireless debugging tap **Pair new device** (shows IP:port and a code):
   ```bash
   adb pair <ip>:<pair-port>        # type the pairing code
   adb connect <ip>:<connect-port>  # the port shown on the Wireless debugging screen
   adb install -r watch/app/build/outputs/apk/debug/app-debug.apk
   ```
4. Open **Safe Maps** on the watch.

## Test it end to end (go / no-go)
1. Backend running (or the Render URL awake: open `/v1/health` first, free plans sleep).
2. Phone web app: Route preferences > Watch check > **On** > **Get pairing code**.
3. Watch: type the 6 digits, press OK, allow the permissions, press OK again. Phone shows **Connected: Galaxy Watch**.
4. Walk with the phone locked for 2 minutes; unlock: readings are on the screen.
5. Watch **Test alert**: it vibrates and shows "Are you OK?". Tap **I'm OK**: the phone shows "You said you are OK".
   Repeat and wait 30 s: the phone shows "Alert would be sent to your contact (demo, not sent)".
6. Phone **Stop and delete readings**: the watch notices on its next reading (within a few seconds) and returns to the code screen.
7. Airplane mode on the watch for 20 s: phone shows "No reading for 15 seconds", then recovers.

No watch handy? `python -m scripts.fake_watch --code <6 digits> --spike --prompt` plays the watch from the laptop.

## Known gaps (v1)
- The prompt vibrates from the background but does not pop the app open; open it from the notification.
- If another app (Samsung Health workout) owns the sensor session, the app falls back to basic heart-rate mode
  without step data, so only **Test alert** can raise the prompt.
- Health Services behaviour is checked against the real library API (the code compiles), but it has not run on a
  real watch yet. Expect small fixes during the first on-watch run.
- Alerts are not sent to a contact (no message provider; OPEN_QUESTIONS 13).
