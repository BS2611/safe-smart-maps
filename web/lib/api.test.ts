import { ApiError, describeError, fetchRoutes, fixturePath, withFreshTimes } from "./api";
import { loadFixture } from "@/test-utils/fixtures";
import { DEFAULT_SETTINGS, type Trip } from "./trip";
import { DEMO_PLACES } from "./places";
import { rawFixture } from "@/test-utils/fixtures";

const trip: Trip = {
  from: DEMO_PLACES[0], to: DEMO_PLACES[1], departISO: "2026-10-25T03:00:00.000Z", settings: DEFAULT_SETTINGS,
};

function respond(body: unknown, status = 200): typeof fetch {
  return (async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;
}

describe("fetchRoutes", () => {
  it("posts the contract body to /v1/routes and parses the response", async () => {
    const calls: { url: string; init: RequestInit }[] = [];
    const fetchImpl = (async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return new Response(JSON.stringify(rawFixture()), { status: 200 });
    }) as unknown as typeof fetch;
    const res = await fetchRoutes(trip, { baseUrl: "http://api.test", fetchImpl, devFixtures: false });
    expect(calls[0].url).toBe("http://api.test/v1/routes");
    expect(calls[0].init.method).toBe("POST");
    expect(JSON.parse(calls[0].init.body as string).from.lat).toBe(DEMO_PLACES[0].lat);
    expect(res.routes.length).toBeGreaterThan(0);
  });

  it("turns contract errors into ApiError with the code", async () => {
    const body = { error: { code: "NO_ROUTE", message: "none" } };
    await expect(fetchRoutes(trip, { fetchImpl: respond(body, 404), devFixtures: false }))
      .rejects.toMatchObject({ code: "NO_ROUTE" });
  });

  it("rejects responses that do not match the contract", async () => {
    await expect(fetchRoutes(trip, { fetchImpl: respond({ routes: "x" }), devFixtures: false }))
      .rejects.toMatchObject({ code: "BAD_RESPONSE" });
    await expect(fetchRoutes(trip, { fetchImpl: respond({ nope: 1 }, 500), devFixtures: false }))
      .rejects.toMatchObject({ code: "BAD_RESPONSE" });
    const notJson = (async () => new Response("<html>", { status: 200 })) as unknown as typeof fetch;
    await expect(fetchRoutes(trip, { fetchImpl: notJson, devFixtures: false }))
      .rejects.toMatchObject({ code: "BAD_RESPONSE" });
  });

  it("reports network failure and cancellation", async () => {
    const down = (async () => { throw new TypeError("failed to fetch"); }) as unknown as typeof fetch;
    await expect(fetchRoutes(trip, { fetchImpl: down, devFixtures: false })).rejects.toMatchObject({ code: "NETWORK" });
    const controller = new AbortController();
    controller.abort();
    const aborted = (async () => { throw new DOMException("aborted", "AbortError"); }) as unknown as typeof fetch;
    await expect(fetchRoutes(trip, { fetchImpl: aborted, devFixtures: false, signal: controller.signal }))
      .rejects.toMatchObject({ code: "CANCELLED" });
  });

  it("times out", async () => {
    const hang = ((_url: string, init: RequestInit) => new Promise((_res, rej) => {
      init.signal?.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")));
    })) as unknown as typeof fetch;
    await expect(fetchRoutes(trip, { fetchImpl: hang, devFixtures: false, timeoutMs: 20 }))
      .rejects.toMatchObject({ code: "UPSTREAM_TIMEOUT" });
  });

  it("dev sample mode reads the matching fixture and sends no request body", async () => {
    const calls: { url: string; init: RequestInit }[] = [];
    const fetchImpl = (async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return new Response(JSON.stringify(rawFixture()), { status: 200 });
    }) as unknown as typeof fetch;
    await fetchRoutes(trip, { fetchImpl, devFixtures: true });
    expect(calls[0].url).toBe("/dev-fixtures/routes_response.json");
    expect(calls[0].init.body).toBeUndefined();
  });
});

describe("fixturePath", () => {
  it("uses the 1 AM sample for the small hours and the 8 PM sample otherwise", () => {
    expect(fixturePath("2026-10-25T08:00:00Z")).toContain("1am");
    expect(fixturePath("2026-10-25T03:00:00Z")).not.toContain("1am");
  });
});

describe("describeError", () => {
  it("writes plain, calm messages for every code", () => {
    const codes = ["NO_ROUTE", "BAD_REQUEST", "NOT_CONFIGURED", "UPSTREAM_TIMEOUT", "UPSTREAM_ERROR",
      "NETWORK", "CANCELLED", "BAD_RESPONSE"] as const;
    for (const code of codes) expect(describeError(new ApiError(code, "Check these fields: to")).length).toBeGreaterThan(10);
    expect(describeError(new ApiError("BAD_REQUEST", "Check these fields: to"))).toBe("Check these fields: to");
    expect(describeError(new Error("x"))).toMatch(/went wrong/);
  });
});

describe("sample data times", () => {
  it("makes sample data look fresh without touching live responses", async () => {
    const now = new Date("2026-10-25T00:00:00Z");
    const fresh = withFreshTimes(loadFixture(), now);
    expect(fresh.data_fetched_at).toBe("2026-10-24T23:56:00.000Z");
    expect(fresh.routes[0].segments[0].data_fetched_at).toBe("2026-10-24T23:56:00.000Z");
    const nulls = withFreshTimes({ ...loadFixture(), data_fetched_at: null }, now);
    expect(nulls.data_fetched_at).toBeNull();

    const fetchImpl = (async () => new Response(JSON.stringify(rawFixture()), { status: 200 })) as unknown as typeof fetch;
    const live = await fetchRoutes(trip, { fetchImpl, devFixtures: false, now });
    expect(live.data_fetched_at).toBe(loadFixture().data_fetched_at);          // live data is never rewritten
    const sample = await fetchRoutes(trip, { fetchImpl, devFixtures: true, now });
    expect(sample.data_fetched_at).toBe("2026-10-24T23:56:00.000Z");
  });
});
