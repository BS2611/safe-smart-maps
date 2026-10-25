import type { CapacitorConfig } from "@capacitor/cli";

// Packs the exported web app (web/out) into an Android app. Build steps: docs/PHONE_TESTING.md section E.
const config: CapacitorConfig = {
  appId: "com.safesmartmaps.app",
  appName: "Safe Smart Maps",
  webDir: "out",
  android: { backgroundColor: "#101413" },
};

export default config;
