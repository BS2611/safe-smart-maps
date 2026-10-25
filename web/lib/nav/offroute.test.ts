import { destination, pointAtDistance, projectOntoRoute, type LngLat } from "./geo";
import { isOffRoute, OFF_ROUTE_ENTER_M, OFF_ROUTE_EXIT_M } from "./offroute";
import { navigationProgress, stepsFromGeometry } from "./steps";

const start: LngLat = [-122.45, 37.8];

describe("off-route detection", () => {
  const coords: LngLat[] = [start, destination(start, 300, 0)];
  const steps = stepsFromGeometry(coords);

  it("stays on the route for a point on the line and a small miss", () => {
    const onLine = destination(start, 80, 0);
    expect(navigationProgress(coords, steps, onLine).offRoute).toBe(false);
    const beside = destination(onLine, 10, 90);
    const near = navigationProgress(coords, steps, beside);
    expect(near.crossTrackM).toBeLessThan(OFF_ROUTE_ENTER_M);
    expect(near.offRoute).toBe(false);
  });

  it("flags a point well off the line, and keeps the flag until the walker is clearly back", () => {
    const onLine = destination(start, 80, 0);
    const away = destination(onLine, 50, 90);
    const off = navigationProgress(coords, steps, away);
    expect(off.crossTrackM).toBeGreaterThan(OFF_ROUTE_ENTER_M);
    expect(off.offRoute).toBe(true);

    expect(isOffRoute(OFF_ROUTE_EXIT_M + 5, true)).toBe(true);
    expect(isOffRoute(OFF_ROUTE_EXIT_M - 1, true)).toBe(false);
    expect(isOffRoute(OFF_ROUTE_ENTER_M - 1, false)).toBe(false);
    const back = navigationProgress(coords, steps, onLine, true);
    expect(back.offRoute).toBe(false);
  });

  it("handles an empty line, a single point, and a distance past the end", () => {
    expect(projectOntoRoute([], start).snapped).toEqual(start);
    expect(projectOntoRoute([start], destination(start, 30, 90)).crossTrackM).toBeGreaterThan(20);
    const mid = destination(start, 100, 0);
    const end = destination(mid, 100, 0);
    const walked = pointAtDistance([start, mid, end], 150);
    expect(walked.bearing).toBeGreaterThanOrEqual(0);
    const clamped = pointAtDistance([start, mid, end], 10_000);
    expect(projectOntoRoute([start, mid, end], clamped.point).alongM).toBeGreaterThan(180);
    expect(pointAtDistance([], 5).point).toEqual([0, 0]);
    expect(pointAtDistance([start], -5).bearing).toBe(0);
  });
});
