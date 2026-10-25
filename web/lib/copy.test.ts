// Regression guard: no UI source file may contain banned wording (never "safe" etc.).
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { findBannedWording } from "./wording";

const ROOTS = ["app", "components"];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return sourceFiles(full);
    return /\.(tsx?|css)$/.test(name) && !/\.test\./.test(name) ? [full] : [];
  });
}

describe("UI copy", () => {
  const files = ROOTS.flatMap((root) => sourceFiles(join(process.cwd(), root)));

  it("finds the UI source files", () => {
    expect(files.length).toBeGreaterThan(0);
  });

  it.each(files.map((f) => [f]))("%s has no banned wording", (file) => {
    const problems = findBannedWording(readFileSync(file, "utf-8"));
    expect(problems).toEqual([]);
  });
});
