import { fakeRelay } from "@/test-utils/fakeRelay";

import { createRelaySource, endTrip, fetchEvents, RelayError, startPairing } from "./watchRelay";
import type { WatchReading } from "./watch";

const opts = (fetchImpl: typeof fetch) => ({ baseUrl: "http://api.test", fetchImpl, pollMs: 1000 });

describe("watch relay client", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("gets a pairing code", async () => {
    const r = fakeRelay();
    const info = await startPairing(opts(r.impl));
    expect(info).toEqual({ tripId: "trip1", pairCode: "123456", expiresInS: 600 });
    expect(r.state.calls[0]).toBe("POST /v1/trips/pair");
  });

  it("turns network failure and 404 into typed errors", async () => {
    const r = fakeRelay();
    r.state.fail = true;
    await expect(startPairing(opts(r.impl))).rejects.toMatchObject({ kind: "NETWORK" });
    r.state.fail = false;
    r.state.ended = true;
    await expect(fetchEvents("trip1", 0, opts(r.impl))).rejects.toBeInstanceOf(RelayError);
    await expect(fetchEvents("trip1", 0, opts(r.impl))).rejects.toMatchObject({ kind: "NOT_FOUND" });
  });

  it("polls, reports only new readings, and keeps the watch label", async () => {
    const r = fakeRelay();
    r.push("paired");
    r.bpm(80);
    const seen: WatchReading[] = [];
    const types: string[] = [];
    const src = createRelaySource("trip1", { onEvent: (e) => types.push(e.type) }, opts(r.impl));
    src.start((x) => seen.push(x));
    await vi.advanceTimersByTimeAsync(0);
    expect(seen.map((x) => x.bpm)).toEqual([80]);
    expect(seen[0].source).toBe("wearos");
    r.bpm(95);
    await vi.advanceTimersByTimeAsync(1000);
    expect(seen.map((x) => x.bpm)).toEqual([80, 95]); // 80 is not delivered twice
    expect(types).toEqual(["paired", "bpm", "bpm"]);
    src.stop();
  });

  it("keeps the simulated label when the sender says simulated", async () => {
    const r = fakeRelay();
    r.push("paired");
    r.bpm(77, "simulated");
    const seen: WatchReading[] = [];
    const src = createRelaySource("trip1", {}, opts(r.impl));
    src.start((x) => seen.push(x));
    await vi.advanceTimersByTimeAsync(0);
    expect(seen[0].source).toBe("simulated");
    src.stop();
  });

  it("stops polling after stop()", async () => {
    const r = fakeRelay();
    const src = createRelaySource("trip1", {}, opts(r.impl));
    src.start(() => {});
    await vi.advanceTimersByTimeAsync(0);
    src.stop();
    const before = r.state.calls.length;
    await vi.advanceTimersByTimeAsync(5000);
    expect(r.state.calls.length).toBe(before);
  });

  it("reports errors, keeps trying on network errors, stops on 404", async () => {
    const r = fakeRelay();
    const errors: string[] = [];
    const src = createRelaySource("trip1", { onError: (e) => errors.push(e.kind) }, opts(r.impl));
    r.state.fail = true;
    src.start(() => {});
    await vi.advanceTimersByTimeAsync(2500);
    expect(errors.length).toBeGreaterThanOrEqual(2);
    expect(new Set(errors)).toEqual(new Set(["NETWORK"]));
    r.state.fail = false;
    r.state.ended = true;
    await vi.advanceTimersByTimeAsync(1000);
    expect(errors.at(-1)).toBe("NOT_FOUND");
    const after = r.state.calls.length;
    await vi.advanceTimersByTimeAsync(5000);
    expect(r.state.calls.length).toBe(after);
  });

  it("endTrip never throws, even when offline", async () => {
    const r = fakeRelay();
    await endTrip("trip1", opts(r.impl));
    expect(r.state.ended).toBe(true);
    r.state.fail = true;
    await expect(endTrip("trip1", opts(r.impl))).resolves.toBeUndefined();
  });
});
