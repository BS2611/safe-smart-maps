import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// next/navigation needs the app router, which does not exist in unit tests.
export const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, back: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
}));

afterEach(() => {
  cleanup();
  push.mockClear();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  try { window.sessionStorage.clear(); } catch { /* ignore */ }
});
