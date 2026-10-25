import { readFileSync } from "node:fs";
import { join } from "node:path";

import { loadFixture } from "@/test-utils/fixtures";

import { BAND_COLOR, BAND_DASH, frameOf, makeProjector, pathFor, segmentPath } from "./geometry";
import { hasGeocoding, parseGeocode, searchPlaces } from "./geocode";
import { CONTINUITY_RULES, FACTORS, factorLabel, SCORE_FORMULA } from "./scoring-info";
import { findBannedWording } from "./wording";

describe("geometry", () => {
  const data = loadFixture();

  it("projects every route point inside the box", () => {
    const project = makeProjector(data.routes, 300, 200, 16);
    for (const [lng, lat] of data.routes.flatMap((r) => r.geometry.coordinates)) {
      const [x, y] = project(lng, lat);
      expect(x).toBeGreaterThanOrEqual(15);
      expect(x).toBeLessThanOrEqual(285);
      expect(y).toBeGreaterThanOrEqual(15);
      expect(y).toBeLessThanOrEqual(185);
    }
  });

  it("keeps north up and east right", () => {
    const project = makeProjector(data.routes, 300, 200);
    const [x1, y1] = project(-122.45, 37.80);
    const [x2, y2] = project(-122.44, 37.81);
    expect(x2).toBeGreaterThan(x1);
    expect(y2).toBeLessThan(y1);
  });

  it("builds path strings and handles empty input", () => {
    const project = makeProjector(data.routes, 300, 200);
    expect(pathFor(data.routes[0].geometry.coordinates, project)).toMatch(/^M[\d.]+,[\d.]+ L/);
    expect(segmentPath(data.routes[0].segments[0], project)).toMatch(/^M.* L/);
    expect(makeProjector([], 100, 50)(0, 0)).toEqual([50, 25]);
    expect(frameOf([], 100, 50).unproject(10, 10)).toEqual([0, 0]);
  });

  it("maps a projected point back to the same longitude and latitude", () => {
    const frame = frameOf(data.routes, 300, 200, 16);
    const [lng, lat] = data.routes[0].geometry.coordinates[0];
    const [x, y] = frame.project(lng, lat);
    const [backLng, backLat] = frame.unproject(x, y);
    expect(backLng).toBeCloseTo(lng, 6);
    expect(backLat).toBeCloseTo(lat, 6);
  });

  it("gives every band a distinct color and a pattern for non-green bands", () => {
    expect(new Set(Object.values(BAND_COLOR)).size).toBe(4);
    expect(BAND_DASH.green).toBeUndefined();
    expect(BAND_DASH.yellow && BAND_DASH.red && BAND_DASH.unknown).toBeTruthy();
  });
});

describe("geocode", () => {
  const payload = { features: [
    { id: "a", properties: { name: "Montgomery BART", place_formatted: "San Francisco" },
      geometry: { coordinates: [-122.4013, 37.7894] } },
    { id: "b", properties: {}, geometry: { coordinates: [1, 2] } },
    { properties: { name: "No coords" } },
  ] };

  it("parses Mapbox results and drops unusable ones", () => {
    const places = parseGeocode(payload);
    expect(places).toEqual([{ id: "a", name: "Montgomery BART, San Francisco", lat: 37.7894, lng: -122.4013 }]);
    expect(parseGeocode(null)).toEqual([]);
    expect(parseGeocode({ features: "x" })).toEqual([]);
  });

  it("does not search without a token or with short text", async () => {
    const never = (async () => { throw new Error("must not be called"); }) as unknown as typeof fetch;
    expect(hasGeocoding(undefined)).toBe(false);
    expect(hasGeocoding("pk.x")).toBe(true);
    expect(await searchPlaces("palace", { token: "", fetchImpl: never })).toEqual([]);
    expect(await searchPlaces("pa", { token: "pk.x", fetchImpl: never })).toEqual([]);
  });

  it("calls Mapbox with the token in the query and favors San Francisco", async () => {
    let seen = "";
    const fetchImpl = (async (url: string) => {
      seen = url;
      return new Response(JSON.stringify(payload), { status: 200 });
    }) as unknown as typeof fetch;
    const places = await searchPlaces("montgomery", { token: "pk.fixture", fetchImpl });
    expect(places).toHaveLength(1);
    expect(seen).toContain("proximity=-122.4193%2C37.7793");
    expect(seen).toContain("access_token=pk.fixture");
  });

  it("throws a clear error when the search service fails", async () => {
    const fetchImpl = (async () => new Response("no", { status: 401 })) as unknown as typeof fetch;
    await expect(searchPlaces("palace", { token: "pk.x", fetchImpl })).rejects.toThrow(/401/);
  });
});

describe("scoring info", () => {
  it("weights equal scoring/scoring_v1.json and sum to 100", () => {
    const config = JSON.parse(readFileSync(join(process.cwd(), "..", "scoring", "scoring_v1.json"), "utf-8"));
    for (const f of FACTORS) {
      expect(f.weight).toBeCloseTo(config.weights[f.id] * 100, 5);
    }
    expect(FACTORS.map((f) => f.id).sort()).toEqual(Object.keys(config.weights).sort());
    expect(FACTORS.reduce((s, f) => s + f.weight, 0)).toBe(100);
  });

  it("continuity numbers equal the config", () => {
    const config = JSON.parse(readFileSync(join(process.cwd(), "..", "scoring", "scoring_v1.json"), "utf-8"));
    expect(CONTINUITY_RULES.coverageTarget / 100).toBe(config.continuity.coverage_target);
    expect(CONTINUITY_RULES.gapLimitM).toBe(config.continuity.gap_limit_m);
    expect(CONTINUITY_RULES.windowM).toBe(config.continuity.window_m);
    expect(CONTINUITY_RULES.coverageRadiusM).toBe(config.radii_m.coverage);
  });

  it("explanations pass the wording rules and activity is labeled an estimate", () => {
    const text = FACTORS.map((f) => `${f.label} ${f.description} ${f.source}`).join(" ") + SCORE_FORMULA;
    expect(findBannedWording(text)).toEqual([]);
    expect(FACTORS.find((f) => f.id === "activity")?.estimate).toBe(true);
    expect(factorLabel("open_places")).toBe("Open places");
    expect(factorLabel("zzz")).toBe("zzz");
  });
});
