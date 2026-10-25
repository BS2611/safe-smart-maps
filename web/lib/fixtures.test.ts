// Contract guard: the backend fixtures must parse with our schema, and the dev copies must be current.
import { existsSync } from "node:fs";
import { join } from "node:path";

import { FIXTURE_DIR, fixtureText, loadFixture } from "@/test-utils/fixtures";

import { RoutesResponseSchema } from "./types";

const NAMES = ["routes_response.json", "routes_response_1am.json"];

describe("backend fixtures", () => {
  it.each(NAMES)("%s matches the schema in lib/types.ts", (name) => {
    const data = loadFixture(name);
    expect(data.api_version).toBe("1");
    expect(data.routes.length).toBeGreaterThan(0);
    for (const route of data.routes) {
      expect(route.segments.length).toBeGreaterThan(0);
      expect(route.geometry.coordinates.length).toBeGreaterThan(1);
    }
  });

  it("rejects a response that drifted from the contract", () => {
    const data = JSON.parse(fixtureText(FIXTURE_DIR, NAMES[0]));
    delete data.routes[0].continuity;
    expect(RoutesResponseSchema.safeParse(data).success).toBe(false);
  });

  it.each(NAMES)("public/dev-fixtures/%s equals tests/fixtures (run npm run sync-fixtures)", (name) => {
    const copy = join(process.cwd(), "public", "dev-fixtures");
    expect(existsSync(join(copy, name))).toBe(true);
    expect(JSON.parse(fixtureText(copy, name))).toEqual(JSON.parse(fixtureText(FIXTURE_DIR, name)));
  });
});
