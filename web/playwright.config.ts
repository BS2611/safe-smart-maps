import { defineConfig, devices } from "@playwright/test";

// Regression viewports: iPhone-class (WebKit), Android-class (Chromium), small Android.
// See docs/specs/AGILE_PLAN.md section 3.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL: "http://localhost:3100", trace: "retain-on-failure" },
  projects: [
    { name: "iphone-webkit", use: { ...devices["iPhone 14"] } },
    { name: "android-chromium", use: { ...devices["Pixel 7"] } },
    {
      name: "small-android-360",
      use: { ...devices["Pixel 7"], viewport: { width: 360, height: 640 } },
    },
  ],
  webServer: {
    command: process.env.CI ? "npm run build && npm run start" : "npm run dev",
    url: "http://localhost:3100",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
