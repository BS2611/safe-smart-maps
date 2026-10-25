import { expect, test } from "@playwright/test";

import { expectNoSideScroll, planDemoTrip, stubApi } from "./helpers";

test.describe("first run", () => {
  test("welcome explains the idea and leads to planning", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "See more of the walk ahead." })).toBeVisible();
    await expect(page.getByText("We do not guarantee safety.")).toBeVisible();
    await expect(page.getByText("In an emergency, call 911.").first()).toBeVisible();
    await expectNoSideScroll(page);
    await page.getByRole("link", { name: /Get started|Enter starting point/ }).click();
    await expect(page).toHaveURL(/\/plan$/);
    await expect(page.getByRole("heading", { name: "Plan your walk" })).toBeVisible();
  });

  test("how scores work lists the weights and the honest limits", async ({ page }) => {
    await page.goto("/how-scores-work");
    await expect(page.getByRole("heading", { name: "1. What we check" })).toBeVisible();
    await expect(page.getByText("100% total")).toBeVisible();
    await expect(page.getByText(/Route score = 50%/)).toBeVisible();
    await expect(page.getByText(/AI can be wrong/)).toBeVisible();
    await expectNoSideScroll(page);
  });
});

test.describe("plan, routes, details", () => {
  test("a full trip: plan, wait, three choices, details", async ({ page }) => {
    const api = await stubApi(page, { delayMs: 400 });
    await planDemoTrip(page);
    await page.getByRole("button", { name: "Show routes" }).click();

    await expect(page).toHaveURL(/\/routes$/);
    await expect(page.getByRole("heading", { name: "Checking your walk", level: 2 })).toBeVisible();
    await expectNoSideScroll(page);

    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();
    await expect(page.getByText("Most lit & active").first()).toBeVisible();
    await expect(page.getByText("Fastest", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/Fetched/).first()).toBeVisible();
    await expect(page.getByText("Sample data")).toHaveCount(0);
    await expectNoSideScroll(page);
    expect(api.requests).toHaveLength(1);
    expect(api.requests[0].depart_time).toMatch(/Z$/);

    await page.getByRole("link", { name: "Details" }).first().click();
    await expect(page.getByRole("heading", { name: "Along the whole walk" })).toBeVisible();
    await page.getByRole("button", { name: "Start" }).click();
    await expect(page.getByRole("region", { name: "Next maneuver" })).toBeVisible();
    await page.getByRole("button", { name: "Simulate walk" }).click();
    await expect(page.getByText("Simulated")).toBeVisible();
    await expectNoSideScroll(page);
    await page.getByRole("button", { name: "End" }).click();
    await expect(page.getByRole("heading", { name: "Along the whole walk" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "What we checked" })).toBeVisible();
    await page.getByRole("group", { name: "Route segments" }).getByRole("button").first().click();
    await expect(page.getByRole("list", { name: "Reasons" })).toBeVisible();
    await expectNoSideScroll(page);

    // Going back must not ask the server again (cached for this trip).
    await page.getByRole("link", { name: "Back to routes" }).click();
    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();
    expect(api.requests).toHaveLength(1);
  });

  test("picking another route changes the explanation panel selection", async ({ page }) => {
    await stubApi(page);
    await planDemoTrip(page);
    await page.getByRole("button", { name: "Show routes" }).click();
    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();
    const fastest = page.getByRole("button", { name: /^Fastest/ });
    await fastest.click();
    await expect(fastest).toHaveAttribute("aria-pressed", "true");
  });

  test("a slow server can be cancelled", async ({ page }) => {
    await stubApi(page, { delayMs: 5000 });
    await planDemoTrip(page);
    await page.getByRole("button", { name: "Show routes" }).click();
    await page.getByRole("button", { name: /Cancel trip check/ }).click();
    await expect(page.getByText("Check cancelled.")).toBeVisible();
  });

  test("preferences are applied and the trip is checked again", async ({ page }) => {
    const api = await stubApi(page);
    await planDemoTrip(page);
    await page.getByRole("button", { name: "Show routes" }).click();
    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();
    await page.getByRole("link", { name: "Route preferences" }).click();
    await page.getByRole("button", { name: "Lighting" }).click();
    await page.getByRole("button", { name: "Apply preferences" }).click();
    await expect(page).toHaveURL(/\/routes$/);
    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();
    expect(api.requests).toHaveLength(2);
  });
});

test.describe("8 PM vs 1 AM", () => {
  test("compares both times and lets the user choose one", async ({ page }) => {
    const api = await stubApi(page);
    await planDemoTrip(page, "1 AM");
    await page.getByRole("button", { name: "Show routes" }).click();
    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();

    await page.getByRole("link", { name: "Compare 8 PM vs 1 AM" }).click();
    await expect(page.getByRole("heading", { name: /Key difference/ })).toBeVisible();
    await expect(page.getByText(/Coverage drops from/)).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();
    await expectNoSideScroll(page);
    const hours = new Set(api.requests.map((r) => r.depart_time));
    expect(hours.size).toBeGreaterThanOrEqual(2);

    await page.getByRole("button", { name: "Use 8:00 PM departure" }).click();
    await expect(page).toHaveURL(/\/routes$/);
    await expect(page.getByText(/8:00 PM/).first()).toBeVisible();
  });
});

test.describe("when things go wrong", () => {
  test("a server problem is explained calmly and a retry works", async ({ page }) => {
    await stubApi(page, { fail: "once" });
    await planDemoTrip(page);
    await page.getByRole("button", { name: "Show routes" }).click();
    await expect(page.locator(".banner.error")).toContainText("not set up yet");
    await expect(page.getByText("In an emergency, call 911.")).toBeVisible();
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();
  });

  test("no connection to the server shows a clear message", async ({ page }) => {
    await stubApi(page, { fail: "abort" });
    await planDemoTrip(page);
    await page.getByRole("button", { name: "Show routes" }).click();
    await expect(page.locator(".banner.error")).toContainText("could not reach the server");
  });

  test("opening routes with no trip asks to plan one", async ({ page }) => {
    await page.goto("/routes");
    await expect(page.getByText("Choose a start and a destination first")).toBeVisible();
  });

  test("every page fits the screen width", async ({ page }) => {
    for (const path of ["/", "/plan", "/preferences", "/how-scores-work", "/routes", "/compare"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expectNoSideScroll(page);
    }
  });

  test("a planned walk fits the phone on plan, routes, detail, and compare", async ({ page }) => {
    await stubApi(page);
    await page.goto("/plan");
    const hint = page.getByText(/Live data covers the demo area/);
    await expect(hint).toBeVisible();
    await hint.scrollIntoViewIfNeeded();
    const sticky = await page.locator(".plan-page .sticky-cta").evaluate((el) => {
      const style = getComputedStyle(el);
      const hintEl = [...document.querySelectorAll("p")].find((node) =>
        (node.textContent ?? "").includes("Live data covers the demo area"));
      const button = el.querySelector("button");
      if (!hintEl || !button) return { opaque: false, overlap: 1, image: style.backgroundImage };
      const hintBox = hintEl.getBoundingClientRect();
      const buttonBox = button.getBoundingClientRect();
      const overlap = Math.min(hintBox.bottom, buttonBox.bottom) - Math.max(hintBox.top, buttonBox.top);
      const color = style.backgroundColor.match(/rgba?\(([^)]+)\)/)?.[1].split(",").map((part) => Number(part.trim())) ?? [];
      const alpha = color.length === 4 ? color[3] : color.length === 3 ? 1 : 0;
      return { opaque: alpha === 1 && style.backgroundImage === "none", overlap, image: style.backgroundImage };
    });
    expect(sticky.opaque).toBe(true);
    expect(sticky.overlap).toBeLessThanOrEqual(0);
    await expectNoSideScroll(page);

    await planDemoTrip(page);
    await expectNoSideScroll(page);
    await page.getByRole("button", { name: "Show routes" }).click();
    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();
    await expectNoSideScroll(page);

    await page.getByRole("link", { name: "Details" }).first().click();
    await expect(page.getByRole("heading", { name: "Along the whole walk" })).toBeVisible();
    await expectNoSideScroll(page);

    await page.goto("/compare");
    await expect(page.getByRole("heading", { name: /Key difference/ })).toBeVisible();
    await expectNoSideScroll(page);
  });
});
