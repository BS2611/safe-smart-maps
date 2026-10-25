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

describe("main's backend", () => {
  it("a real response produced by main's backend (labeled fakes) is accepted by the web schema", () => {
    // tests/fixtures/routes_response_main_backend.json was generated with main's own planner and fakes.
    // Regenerate it when main's response shape changes; this test then shows whether the UI still fits.
    const data = loadFixture("routes_response_main_backend.json");
    expect(data.routes.length).toBeGreaterThan(0);
    const raw = JSON.parse(fixtureText(FIXTURE_DIR, "routes_response_main_backend.json"));
    expect(raw.routes[0].segments[0]).toHaveProperty("unknown_factors");   // main adds fields; they are tolerated
  });
});
