import { loadFixture } from "@/test-utils/fixtures";

import { averageFactors, compareTimes } from "./routeStats";
import { SOURCES, sourceStatuses, STATUS_TEXT } from "./sources";
import { findBannedWording } from "./wording";

const early = loadFixture();
const late = loadFixture("routes_response_1am.json");

describe("averageFactors", () => {
  it("averages each factor over the route and uses null when never known", () => {
    const route = early.routes[0];
    const avg = averageFactors(route);
    expect(Object.keys(avg).sort()).toEqual(Object.keys(route.segments[0].factors).sort());
    expect(avg.transit).toBeNull();                     // transit is not connected in the fixtures
    expect(avg.turns).toBeGreaterThan(0);
    for (const v of Object.values(avg)) if (v !== null) expect(v).toBeGreaterThanOrEqual(0);
  });

  it("weights by segment length", () => {
    const route = structuredClone(early.routes[0]);
    route.segments = route.segments.slice(0, 2).map((s, i) => ({
      ...s, length_m: i === 0 ? 100 : 300, factors: { turns: i === 0 ? 100 : 20 },
    }));
    expect(averageFactors(route).turns).toBe(40);
  });
});

describe("compareTimes", () => {
  it("reports a coverage drop and the longer empty stretch", () => {
    const c = compareTimes(early, late);
    expect(c.coverageDelta).toBeLessThan(0);
    expect(c.headline).toMatch(/^Coverage drops from \d+% to \d+%\.$/);
    expect(c.detail).toMatch(/longest empty stretch grows/);
    expect(c.openEarly).toBeGreaterThan(c.openLate as number);
    expect(c.detail).toMatch(/fewer open places/);
  });

  it("says when the recommended route changes", () => {
    const changed = structuredClone(late);
    changed.routes[0].route_id = "r-other";
    changed.routes[0].via = ["Van Ness Ave"];
    const c = compareTimes(early, changed);
    expect(c.routeChanged).toBe(true);
    expect(c.detail).toMatch(/changes to a different route \(via Van Ness Ave\)/);
    expect(compareTimes(early, late).routeChanged).toBe(false);
    expect(compareTimes(early, late).detail).toMatch(/same route is recommended/);
  });

  it("reports a rise, and 'about the same' for small changes", () => {
    expect(compareTimes(late, early).headline).toMatch(/^Coverage rises/);
    expect(compareTimes(early, early).headline).toBe("Conditions are about the same at both times.");
  });

  it("is honest when coverage is unknown", () => {
    const unknown = structuredClone(late);
    unknown.routes[0].continuity.coverage_pct = null;
    const c = compareTimes(early, unknown);
    expect(c.coverageDelta).toBeNull();
    expect(c.headline).toMatch(/not sure/);
  });

  it("never uses banned wording", () => {
    const c = compareTimes(early, late);
    expect(findBannedWording(`${c.headline} ${c.detail}`)).toEqual([]);
  });
});

describe("sources", () => {
  it("shows every check as 'Checking' while loading", () => {
    const s = sourceStatuses("loading");
    expect(Object.values(s).every((v) => v === "checking")).toBe(true);
    expect(Object.keys(s)).toHaveLength(SOURCES.length);
  });

  it("marks only the sources named in warnings as not sure", () => {
    const s = sourceStatuses("success", [
      "Live business listings: not available right now (failed).",
      "Transit schedules are not connected, so transit shows as not sure.",
    ]);
    expect(s.places).toBe("unavailable");
    expect(s.transit).toBe("unavailable");
    expect(s.lighting).toBe("done");
    expect(s.routes).toBe("done");
    expect(STATUS_TEXT.unavailable).toBe("Not sure");
  });

  it("matches the warning text the server really sends", () => {
    const warnings = early.warnings.concat(late.warnings);
    const s = sourceStatuses("success", warnings);
    expect(s.transit).toBe("unavailable");   // the fixtures carry the real transit warning
  });
});
