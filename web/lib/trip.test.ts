import {
  clearTrip, DEFAULT_SETTINGS, departDate, EMPTY_TRIP, isReady, loadTrip, MAX_PRIORITIES, saveTrip,
  togglePriority, toRequestBody, type Trip,
} from "./trip";
import { DEMO_PLACES } from "./places";

const [palace, montgomery] = DEMO_PLACES;
const trip: Trip = { from: palace, to: montgomery, departISO: "2026-10-25T03:00:00.000Z", settings: DEFAULT_SETTINGS };

class MemoryStorage {
  data = new Map<string, string>();
  getItem(k: string) { return this.data.get(k) ?? null; }
  setItem(k: string, v: string) { this.data.set(k, v); }
  removeItem(k: string) { this.data.delete(k); }
}

describe("priorities", () => {
  it("lets the user pick at most two", () => {
    let p: string[] = [];
    p = togglePriority(p, "lighting");
    p = togglePriority(p, "open_places");
    expect(p).toHaveLength(MAX_PRIORITIES);
    expect(togglePriority(p, "transit")).toEqual(p);            // third is ignored
    expect(togglePriority(p, "lighting")).toEqual(["open_places"]); // toggle off
  });
});

describe("trip readiness and request body", () => {
  it("needs two different places", () => {
    expect(isReady(EMPTY_TRIP)).toBe(false);
    expect(isReady({ ...trip, to: palace })).toBe(false);
    expect(isReady(trip)).toBe(true);
  });

  it("builds the contract request body", () => {
    const body = toRequestBody(trip);
    expect(body).toEqual({
      from: { lat: palace.lat, lng: palace.lng },
      to: { lat: montgomery.lat, lng: montgomery.lng },
      depart_time: "2026-10-25T03:00:00.000Z",
      settings: { max_extra_minutes: 10, with_companion: false, priorities: [] },
    });
    expect(body.depart_time).toMatch(/Z$/); // always a time zone
  });

  it("uses now when the trip says leave now", () => {
    const now = new Date("2026-10-25T08:00:00Z");
    expect(departDate({ ...trip, departISO: null }, now)).toEqual(now);
    expect(() => toRequestBody(EMPTY_TRIP)).toThrow(/start and a destination/);
  });
});

describe("session storage", () => {
  it("saves, loads and clears", () => {
    const s = new MemoryStorage();
    saveTrip(trip, s);
    expect(loadTrip(s)).toEqual(trip);
    clearTrip(s);
    expect(loadTrip(s)).toEqual(EMPTY_TRIP);
  });

  it("falls back safely on bad or blocked storage", () => {
    const bad = { getItem: () => "{not json" };
    expect(loadTrip(bad)).toEqual(EMPTY_TRIP);
    const blocked = { getItem: () => { throw new Error("blocked"); } };
    expect(loadTrip(blocked)).toEqual(EMPTY_TRIP);
    expect(() => saveTrip(trip, { setItem: () => { throw new Error("full"); } })).not.toThrow();
    expect(() => clearTrip({ removeItem: () => { throw new Error("x"); } })).not.toThrow();
    expect(() => saveTrip(trip, undefined)).not.toThrow();
  });

  it("fills missing settings with defaults", () => {
    const s = new MemoryStorage();
    s.setItem("ssm.trip.v1", JSON.stringify({ from: palace, to: montgomery, settings: { maxExtraMinutes: 5 } }));
    expect(loadTrip(s).settings).toEqual({ ...DEFAULT_SETTINGS, maxExtraMinutes: 5 });
  });
});
