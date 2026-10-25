import { evaluateCheckIn, onDarkestStretch, pingPairedWatch } from "./checkin";

const base = {
  enabled: true,
  nowMs: 10_000,
  lastAckMs: 0,
  intervalMs: 5_000,
  onDarkest: false,
  darkestLatched: false,
  showing: false,
};

describe("evaluateCheckIn", () => {
  it("stays quiet when the preference is off", () => {
    expect(evaluateCheckIn({ ...base, enabled: false, onDarkest: true })).toEqual({
      open: null, darkestLatched: false,
    });
  });

  it("opens on the interval and not again while the prompt is up", () => {
    expect(evaluateCheckIn(base).open).toBe("interval");
    expect(evaluateCheckIn({ ...base, showing: true })).toEqual({ open: null, darkestLatched: false });
    expect(evaluateCheckIn({ ...base, nowMs: 4_000 }).open).toBeNull();
  });

  it("opens on the darkest stretch once per visit", () => {
    expect(evaluateCheckIn({ ...base, onDarkest: true, nowMs: 1_000 }).open).toBe("darkest");
    const held = evaluateCheckIn({ ...base, onDarkest: true, darkestLatched: true, nowMs: 1_000 });
    expect(held).toEqual({ open: null, darkestLatched: true });
    const left = evaluateCheckIn({ ...base, onDarkest: false, darkestLatched: true, nowMs: 1_000 });
    expect(left.darkestLatched).toBe(false);
    expect(evaluateCheckIn({ ...base, onDarkest: true, darkestLatched: false, nowMs: 1_000 }).open).toBe("darkest");
  });

  it("prefers the darkest stretch when the timer is also due", () => {
    expect(evaluateCheckIn({ ...base, onDarkest: true }).open).toBe("darkest");
  });
});

describe("onDarkestStretch", () => {
  const segments = [
    { score: 80, start: [0, 0] as [number, number], end: [0, 0.001] as [number, number] },
    { score: 10, start: [0, 0.001] as [number, number], end: [0, 0.002] as [number, number] },
    { score: null, start: [0, 0.002] as [number, number], end: [0, 0.003] as [number, number] },
  ];

  it("is true only on the lowest known score", () => {
    expect(onDarkestStretch(segments, 0, 0.0015)).toBe(true);
    expect(onDarkestStretch(segments, 0, 0)).toBe(false);
    expect(onDarkestStretch([], 0, 0)).toBe(false);
  });
});

describe("pingPairedWatch", () => {
  it("does not pretend a watch was reached", () => {
    expect(pingPairedWatch("interval")).toBe("unavailable");
    expect(pingPairedWatch("darkest")).toBe("unavailable");
  });
});
