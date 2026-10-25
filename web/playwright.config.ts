import { defineConfig, devices } from "@playwright/test";

// Regression viewports: iPhone-class (WebKit), Android-class (Chromium), small Android.
// See docs/specs/AGILE_PLAN.md section 3.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  workers: process.env.CI ? 2 : 3,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  expect: { timeout: 10_000 },
  use: { baseURL: "http://localhost:3101", trace: "retain-on-failure" },
  projects: [
    { name: "iphone-webkit", use: { ...devices["iPhone 14"] } },
    { name: "android-chromium", use: { ...devices["Pixel 7"] } },
    {
      name: "small-android-360",
      use: { ...devices["Pixel 7"], viewport: { width: 360, height: 640 } },
    },
  ],
  webServer: {
    // Port 3101 keeps tests away from the developer's own server on 3000. Sample-data mode is
    // forced off so the tests exercise the real request path (answered by the stubs in e2e/).
    // Tests run against a production build (what users get; React dev mode double-runs effects).
    command: "npm run build && npx next start -p 3101",
    url: "http://localhost:3101",
    reuseExistingServer: false,
    timeout: 240_000,
    env: { NEXT_PUBLIC_DEV_FIXTURES: "0", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000", NEXT_PUBLIC_MAPBOX_TOKEN: "" },
  },
});
