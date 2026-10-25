import { vi } from "vitest";

import type { RelayEvent } from "@/lib/watchRelay";

/** A tiny in-memory stand-in for the relay endpoints. Calls are recorded for assertions. */
export function fakeRelay() {
  const state = { events: [] as RelayEvent[], paired: false, ended: false, calls: [] as string[], fail: false };
  let nextId = 1;
  const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

  const impl = vi.fn(async (url: string, init?: RequestInit) => {
    const path = url.replace(/^https?:\/\/[^/]+/, "");
    const method = init?.method ?? "GET";
    state.calls.push(`${method} ${path}`);
    if (state.fail) throw new TypeError("offline");
    if (path === "/v1/trips/pair") return json({ trip_id: "trip1", pair_code: "123456", expires_in_s: 600 });
    if (path.startsWith("/v1/trips/trip1/events")) {
      if (state.ended) return json({ error: { code: "NOT_FOUND", message: "x" } }, 404);
      const after = Number(new URL(url).searchParams.get("after") ?? 0);
      const latest = [...state.events].reverse().find((e) => e.type === "bpm");
      return json({
        status: state.paired ? "paired" : "waiting",
        latest: latest ? { bpm: latest.bpm, ts: latest.ts, source: latest.source } : null,
        events: state.events.filter((e) => e.id > after),
        next_after: nextId - 1,
      });
    }
    if (path === "/v1/trips/trip1/end") { state.ended = true; return new Response(null, { status: 204 }); }
    return json({}, 404);
  });

  const push = (type: RelayEvent["type"], extra: Partial<RelayEvent> = {}) => {
    if (type === "paired") state.paired = true;
    state.events.push({ id: nextId++, type, ...extra });
  };
  const bpm = (value: number, source: RelayEvent["source"] = "wearos") =>
    push("bpm", { bpm: value, ts: "2026-10-25T10:00:00.000Z", source });

  return { impl: impl as unknown as typeof fetch, state, push, bpm };
}
