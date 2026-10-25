// Copies the labeled API fixtures from tests/fixtures into web/public/dev-fixtures.
// Used only by the dev "sample data" mode (NEXT_PUBLIC_DEV_FIXTURES=1) and by Playwright.
// lib/fixtures.test.ts fails if the copies drift from the originals.
import { cpSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const from = join(process.cwd(), "..", "tests", "fixtures");
const to = join(process.cwd(), "public", "dev-fixtures");
mkdirSync(to, { recursive: true });
for (const name of ["routes_response.json", "routes_response_1am.json"]) {
  cpSync(join(from, name), join(to, name));
  console.log(`copied ${name}`);
}
