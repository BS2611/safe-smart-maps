import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": new URL(".", import.meta.url).pathname } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["node_modules", "e2e", ".next"],
    coverage: {
      provider: "v8",
      include: ["components/**", "lib/**"],
      exclude: ["**/*.test.*"],
      thresholds: { lines: 80, functions: 80, branches: 80, statements: 80 },
    },
  },
});
