#!/usr/bin/env bash
# Builds the debug APK from the command line (Windows, Git Bash). Run from anywhere:
#   bash web/scripts/build-apk.sh            sample-data app (works without a backend)
#   bash web/scripts/build-apk.sh --live     talks to NEXT_PUBLIC_API_BASE_URL
# Result: web/android/app/build/outputs/apk/debug/app-debug.apk
#
# One-time setup (see docs/PHONE_TESTING.md section E): Android SDK in %USERPROFILE%\Android\Sdk and a
# JDK 17-21 in %USERPROFILE%\Android\jdk\<jdk folder>. Gradle 8.14 does not run on Java 24 or newer.
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

USER_HOME="$(cd ~ && pwd -W 2>/dev/null || pwd)"
JDK_DIR="$(ls -d "$HOME"/Android/jdk/jdk-* 2>/dev/null | sort | tail -1 || true)"
[ -n "$JDK_DIR" ] || { echo "No JDK found in ~/Android/jdk (install Temurin 21 there)"; exit 1; }
[ -d "$HOME/Android/Sdk/platforms" ] || { echo "No Android SDK in ~/Android/Sdk"; exit 1; }

export JAVA_HOME="$(cd "$JDK_DIR" && pwd -W 2>/dev/null || echo "$JDK_DIR")"
# A long temp path makes Java on Windows fail with "Unable to establish loopback connection".
mkdir -p /c/tmp
export TEMP='C:\tmp' TMP='C:\tmp' GRADLE_OPTS="-Djava.io.tmpdir=C:/tmp"

node scripts/build-android.mjs "$@"
printf 'sdk.dir=%s/Android/Sdk\n' "$USER_HOME" | sed 's#\\#/#g' > android/local.properties
cd android
./gradlew.bat assembleDebug --no-daemon
ls -la app/build/outputs/apk/debug/app-debug.apk
