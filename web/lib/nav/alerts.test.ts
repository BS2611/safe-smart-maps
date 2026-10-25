import { loadFixture } from "@/test-utils/fixtures";
import type { Route, Segment } from "@/lib/types";

import { alertAhead } from "./alerts";

describe("stretch heads-up", () => {
  const route = loadFixture().routes[0];
  const base = route.segments[0];

  function one(over: Partial<Segment>): Route {
    return { ...route, segments: [{ ...base, length_m: 400, ...over }] };
  }

  it("warns when the next stretch is low-scoring or has no open places", () => {
    const alert = alertAhead(route, 0, 20);
    expect(alert).not.toBeNull();
    expect(alert?.title).toMatch(/Next stretch|Open places thin out/);
    expect(alert?.detail).toMatch(/Score/);
  });

  it("stays quiet on an empty route or a well supported stretch", () => {
    expect(alertAhead({ ...route, segments: [] }, 0)).toBeNull();
    expect(alertAhead(one({
      band: "green", score: 80, reasons: ["shops nearby"],
      factors: { ...base.factors, open_places: 3 },
    }), 0)).toBeNull();
  });

  it("separates a gap from a low score, including a score that is not sure", () => {
    const gap = alertAhead(one({
      band: "green", score: 70, reasons: ["no open places nearby"],
      factors: { ...base.factors, open_places: 1 },
    }), 0);
    expect(gap?.title).toBe("Open places thin out ahead");

    const low = alertAhead(one({
      band: "red", score: null, reasons: ["lit street"],
      factors: { ...base.factors, open_places: 2 },
    }), 0);
    expect(low?.kind).toBe("low");
    expect(low?.detail).toBe("Score Not sure.");

    const yellow = alertAhead(one({
      band: "yellow", score: 41.2, reasons: ["mixed"],
      factors: { ...base.factors, open_places: 2 },
    }), 0);
    expect(yellow?.title).toMatch(/Mixed/);
    expect(yellow?.detail).toBe("Score 41 / 100.");
  });
});
