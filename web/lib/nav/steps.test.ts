import { destination, type LngLat } from "./geo";
import { fetchMapboxSteps, navigationProgress, stepsFromGeometry, stepsFromMapbox } from "./steps";

const start: LngLat = [-122.45, 37.8];

function cornerRoute(): LngLat[] {
  const turn = destination(start, 200, 0);
  const end = destination(turn, 180, 90);
  return [start, turn, end];
}

describe("step progression", () => {
  const coords = cornerRoute();
  const steps = stepsFromGeometry(coords);

  it("builds a depart, a right turn, and an arrival", () => {
    expect(steps.map((step) => step.type)).toEqual(["depart", "turn", "arrive"]);
    expect(steps[1].instruction).toBe("Turn right");
    expect(steps[1].street).toBeNull();
  });

  it("shows the upcoming turn, then continues after the corner", () => {
    const atStart = navigationProgress(coords, steps, start);
    expect(atStart.instruction).toBe("Turn right");
    expect(atStart.distanceToManeuverM).toBeGreaterThan(180);
    expect(atStart.distanceToManeuverM).toBeLessThan(210);
    expect(atStart.stepIndex).toBe(1);

    const before = destination(start, 170, 0);
    const near = navigationProgress(coords, steps, before);
    expect(near.instruction).toBe("Turn right");
    expect(near.distanceToManeuverM).toBeGreaterThan(20);
    expect(near.distanceToManeuverM).toBeLessThan(40);

    const turn = destination(start, 200, 0);
    const past = destination(turn, 30, 90);
    const after = navigationProgress(coords, steps, past);
    expect(after.stepIndex).toBe(2);
    expect(after.instruction).toBe("Continue straight");
    expect(after.remainingDistanceM).toBeLessThan(atStart.remainingDistanceM);
  });

  it("advances once the walker is within a few meters of the maneuver", () => {
    const turn = destination(start, 200, 0);
    const almost = destination(turn, 8, 180);
    const progress = navigationProgress(coords, steps, almost);
    expect(progress.instruction).not.toBe("Turn right");
  });

  it("says arrive when the destination is close", () => {
    const turn = destination(start, 200, 0);
    const end = destination(turn, 180, 90);
    const progress = navigationProgress(coords, steps, end);
    expect(progress.instruction).toBe("Arrive");
    expect(progress.distanceToManeuverM).toBeLessThan(5);
  });

  it("reads Mapbox steps, including the street name", () => {
    const parsed = stepsFromMapbox({
      routes: [{
        legs: [{
          steps: [
            {
              name: "Bay Street",
              distance: 120,
              duration: 90,
              maneuver: { type: "turn", modifier: "left", instruction: "Turn left onto Bay Street", location: [-122.45, 37.8] },
            },
            {
              name: "",
              distance: 0,
              duration: 0,
              maneuver: { type: "arrive", location: [-122.44, 37.81] },
            },
          ],
        }],
      }],
    });
    expect(parsed[0]).toMatchObject({ instruction: "Turn left onto Bay Street", street: "Bay Street", type: "turn" });
    expect(parsed[1].street).toBeNull();
    expect(parsed[1].instruction).toBe("Arrive");
  });

  it("heads out on a straight line and names sharp turns", () => {
    const end = destination(start, 400, 0);
    const straight = stepsFromGeometry([start, end]);
    expect(straight.map((step) => step.type)).toEqual(["depart", "arrive"]);
    expect(navigationProgress([start, end], straight, start).instruction).toBe("Head out");

    const turn = destination(start, 100, 0);
    const sharp = destination(turn, 100, 140);
    const around = destination(turn, 80, 190);
    const sharpSteps = stepsFromGeometry([start, turn, sharp]);
    const uTurn = stepsFromGeometry([start, turn, around]);
    expect(sharpSteps[1].instruction).toMatch(/sharp right|Turn sharp right/);
    expect(uTurn[1].instruction).toBe("Make a U-turn");
  });

  it("loads Mapbox steps and gives up when the request fails", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        routes: [{ legs: [{ steps: [{ name: "Columbus Avenue", distance: 40, duration: 30, maneuver: { type: "depart", location: start } }] }] }],
      }),
    } as Response);
    const loaded = await fetchMapboxSteps([start, destination(start, 50, 0), destination(start, 90, 10)], "pk.test");
    expect(loaded?.[0].street).toBe("Columbus Avenue");
    expect(fetchSpy.mock.calls[0][0]).toEqual(expect.stringContaining("access_token=pk.test"));
    expect(String(fetchSpy.mock.calls[0][0])).not.toContain(" ");

    fetchSpy.mockResolvedValueOnce({ ok: false, json: async () => ({}) } as Response);
    await expect(fetchMapboxSteps(cornerRoute(), "pk.test")).resolves.toBeNull();
    fetchSpy.mockRejectedValueOnce(new Error("offline"));
    await expect(fetchMapboxSteps(cornerRoute(), "pk.test")).resolves.toBeNull();
    fetchSpy.mockRestore();
  });

  it("ignores a broken Mapbox payload and skips the network without a token", async () => {
    expect(stepsFromMapbox(null)).toEqual([]);
    expect(stepsFromMapbox({ routes: [] })).toEqual([]);
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    await expect(fetchMapboxSteps(coords, "  ")).resolves.toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
