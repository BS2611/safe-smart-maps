import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { Page, Route } from "@playwright/test";

const DIR = join(process.cwd(), "..", "tests", "fixtures");

function fixture(name: string) {
  return JSON.parse(readFileSync(join(DIR, name), "utf-8"));
}

function hourInLA(iso: string): number {
  return Number(new Intl.DateTimeFormat("en-US", { hour: "numeric", hourCycle: "h23", timeZone: "America/Los_Angeles" })
    .format(new Date(iso)));
}

export type ApiStub = { requests: { depart_time: string }[] };

/** Answers POST /v1/routes with the backend's labeled fixtures (no backend needed in browser tests). */
export async function stubApi(page: Page, options: { delayMs?: number; fail?: "503" | "abort" | "once" } = {}): Promise<ApiStub> {
  const stub: ApiStub = { requests: [] };
  let failed = false;
  await page.route("**/v1/routes", async (route: Route) => {
    const body = route.request().postDataJSON();
    stub.requests.push({ depart_time: body.depart_time });
    if (options.delayMs) await new Promise((r) => setTimeout(r, options.delayMs));
    if (options.fail === "abort") return route.abort("connectionrefused");
    if (options.fail === "503" || (options.fail === "once" && !failed)) {
      failed = true;
      return route.fulfill({
        status: 503, contentType: "application/json",
        body: JSON.stringify({ error: { code: "NOT_CONFIGURED", message: "Routing is not set up on the server." } }),
      });
    }
    const data = hourInLA(body.depart_time) < 5 ? fixture("routes_response_1am.json") : fixture("routes_response.json");
    return route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(data) });
  });
  // The browser sends a CORS preflight to the other port first.
  await page.route("**/v1/routes", (route) => route.request().method() === "OPTIONS"
    ? route.fulfill({ status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "content-type", "access-control-allow-methods": "POST" } })
    : route.fallback());
  return stub;
}

export async function planDemoTrip(page: Page, when: "8 PM" | "1 AM" | "Now" = "8 PM") {
  await page.goto("/plan");
  await page.getByRole("button", { name: "Palace of Fine Arts" }).first().click();
  await page.getByRole("button", { name: "Montgomery BART Station" }).last().click();
  await page.getByRole("button", { name: when }).click();
}

export async function expectNoSideScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 0) throw new Error(`Page scrolls sideways by ${overflow}px at ${page.url()}`);
}
