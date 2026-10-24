import { expect, test } from "@playwright/test";

test("home shows the name, the honesty notice and the emergency line", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Safe Smart Maps" })).toBeVisible();
  await expect(page.getByText("We do not guarantee safety.")).toBeVisible();
  await expect(page.getByText("In an emergency, call 911.")).toBeVisible();
});

test("page does not scroll sideways on this viewport", async ({ page }) => {
  await page.goto("/");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
