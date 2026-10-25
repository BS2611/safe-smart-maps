import type { CapacitorConfig } from "@capacitor/cli";

// Next's static export writes HTML to `out` when distDir is `.next`.
// When NEXT_DIST_DIR is set (`.next-android` in the Android check), Next uses
// that folder as the export directory instead. Sync must read the same folder.
const customExportDir = process.env.NEXT_DIST_DIR;
const webDir =
  process.env.BUILD_TARGET === "android" && customExportDir && customExportDir !== ".next"
    ? customExportDir
    : "out";

// Packs the exported web app into an Android app. Build steps: docs/PHONE_TESTING.md section E.
const config: CapacitorConfig = {
  appId: "com.safesmartmaps.app",
  appName: "Safe Smart Maps",
  webDir,
  android: { backgroundColor: "#101413" },
};

export default config;
