import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { planDemoTrip, stubApi } from "./helpers";

// Automated accessibility check (WCAG 2.1 A/AA rules, including color contrast) on every screen.
async function expectNoViolations(page: import("@playwright/test").Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const summary = results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(" | ")}`);
  expect(summary).toEqual([]);
}

test.describe("accessibility", () => {
  for (const path of ["/", "/plan", "/preferences", "/how-scores-work"]) {
    test(`${path} has no WCAG A/AA violations`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expectNoViolations(page);
    });
  }

  test("results, details and comparison have no violations", async ({ page }) => {
    await stubApi(page);
    await planDemoTrip(page);
    await page.getByRole("button", { name: "Show routes" }).click();
    await expect(page.getByRole("heading", { name: "Why this route" })).toBeVisible();
    await expectNoViolations(page);
    await page.getByRole("link", { name: "Details" }).first().click();
    await expect(page.getByRole("heading", { name: "Along the whole walk" })).toBeVisible();
    await page.getByRole("group", { name: "Route segments" }).getByRole("button").first().click();
    await expectNoViolations(page);
    await page.getByRole("link", { name: "Back to routes" }).click();
    await page.getByRole("link", { name: "Compare 8 PM vs 1 AM" }).click();
    await expect(page.getByRole("heading", { name: /Key difference/ })).toBeVisible();
    await expectNoViolations(page);
  });

  test("error and checking states have no violations", async ({ page }) => {
    await stubApi(page, { fail: "503" });
    await planDemoTrip(page);
    await page.getByRole("button", { name: "Show routes" }).click();
    await expect(page.locator(".banner.error")).toBeVisible();
    await expectNoViolations(page);
  });

  test("touch targets are at least 44 px", async ({ page }) => {
    await page.goto("/plan");
    const small = await page.evaluate(() => [...document.querySelectorAll("button, a.btn, a.icon-btn, input, summary")]
      .map((el) => ({ el: el as HTMLElement, r: (el as HTMLElement).getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && (r.height < 43.5 || r.width < 43.5))
      .map(({ el }) => `${el.tagName.toLowerCase()} ${el.textContent?.trim().slice(0, 20) || el.getAttribute("aria-label")}`));
    expect(small).toEqual([]);
  });
});
