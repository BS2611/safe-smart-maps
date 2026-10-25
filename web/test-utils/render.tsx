import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

import { TripProvider } from "@/components/TripProvider";
import { DEFAULT_SETTINGS, EMPTY_TRIP, type Trip } from "@/lib/trip";
import { DEMO_PLACES } from "@/lib/places";
import { rawFixture } from "./fixtures";

export const READY_TRIP: Trip = {
  from: DEMO_PLACES[0], to: DEMO_PLACES[1], departISO: "2026-10-25T03:00:00.000Z", settings: DEFAULT_SETTINGS,
};

export function renderWithTrip(ui: ReactElement, trip: Trip = EMPTY_TRIP): RenderResult {
  return render(<TripProvider initialTrip={trip}>{ui}</TripProvider>);
}

type FetchPlan = {
  /** Called for each request; return a body or an Error. */
  respond?: (body: { depart_time: string } | null, url: string) => unknown;
  status?: number;
  delayMs?: number;
};

/** Replaces global fetch for tests. Calls are recorded in the returned array. */
export function stubFetch(plan: FetchPlan = {}) {
  const calls: { url: string; body: { depart_time: string } | null }[] = [];
  const impl = vi.fn(async (url: string, init?: RequestInit) => {
    const body = init?.body ? JSON.parse(init.body as string) : null;
    calls.push({ url, body });
    if (plan.delayMs) await new Promise((r) => setTimeout(r, plan.delayMs));
    const result = plan.respond ? plan.respond(body, url) : rawFixture();
    if (result instanceof Error) throw result;
    return new Response(JSON.stringify(result), { status: plan.status ?? 200 });
  });
  vi.stubGlobal("fetch", impl);
  return { calls, impl };
}

export function fixtureFor(departISO: string | undefined) {
  const hour = Number(new Intl.DateTimeFormat("en-US", {
    hour: "numeric", hourCycle: "h23", timeZone: "America/Los_Angeles",
  }).format(new Date(departISO ?? "2026-10-25T03:00:00Z")));
  return rawFixture(hour < 5 ? "routes_response_1am.json" : "routes_response.json");
}
