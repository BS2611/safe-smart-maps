// Builds the web app as static files and copies them into the Android project.
//   node scripts/build-android.mjs            sample-data build (works without a backend)
//   node scripts/build-android.mjs --live     talks to the backend at NEXT_PUBLIC_API_BASE_URL
// Public keys come from web/.env.local (git-ignored). Nothing secret is added to the app.
import { spawnSync } from "node:child_process";

const live = process.argv.includes("--live");
const env = {
  ...process.env,
  BUILD_TARGET: "android",
  NEXT_PUBLIC_DEV_FIXTURES: live ? "0" : "1",
};
const run = (cmd, args) => {
  const r = spawnSync(cmd, args, { stdio: "inherit", env, shell: true });
  if (r.status !== 0) process.exit(r.status ?? 1);
};

console.log(`Building the Android web bundle (${live ? "live backend" : "sample data"})...`);
run("npx", ["next", "build"]);
console.log("Copying into the Android project...");
run("npx", ["cap", "sync", "android"]);
console.log("Done. Open web/android in Android Studio, or run: cd android && gradlew assembleDebug");
