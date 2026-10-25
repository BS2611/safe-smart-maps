import { createSimulatedSource, isSimulated, nextSimulatedBpm, SIMULATED_RANGE, sourceLabel, type WatchReading } from "./watch";

describe("watch helpers", () => {
  it("always labels the simulated source as Simulated", () => {
    expect(sourceLabel("simulated")).toBe("Simulated");
    expect(isSimulated("simulated")).toBe(true);
    expect(isSimulated("wearos")).toBe(false);
    expect(sourceLabel("wearos")).toBe("Galaxy Watch");
  });

  it("keeps the simulated bpm inside the range", () => {
    expect(nextSimulatedBpm(SIMULATED_RANGE.max, () => 1)).toBe(SIMULATED_RANGE.max);
    expect(nextSimulatedBpm(SIMULATED_RANGE.min, () => 0)).toBe(SIMULATED_RANGE.min);
    expect(nextSimulatedBpm(90, () => 0.5)).toBe(90);
  });
});

describe("createSimulatedSource", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("emits a labeled reading at once, then on each interval, and stops cleanly", () => {
    const seen: WatchReading[] = [];
    const src = createSimulatedSource({ intervalMs: 1000, rng: () => 0.5 });
    src.start((r) => seen.push(r));
    expect(seen).toHaveLength(1);
    vi.advanceTimersByTime(3000);
    expect(seen).toHaveLength(4);
    expect(seen.every((r) => r.source === "simulated")).toBe(true);
    src.stop();
    vi.advanceTimersByTime(5000);
    expect(seen).toHaveLength(4);
  });

  it("ignores a second start while running", () => {
    const seen: WatchReading[] = [];
    const src = createSimulatedSource({ intervalMs: 1000 });
    src.start((r) => seen.push(r));
    src.start((r) => seen.push(r));
    expect(seen).toHaveLength(1);
    src.stop();
  });
});
