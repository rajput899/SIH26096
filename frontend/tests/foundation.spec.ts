import { expect, test } from "@playwright/test";

test("frontend displays the real backend dependency report", async ({ page, request }) => {
  const health = await request.get("/api/health");
  expect([200, 503]).toContain(health.status());
  const report = await health.json();
  expect(["ready", "degraded"]).toContain(report.status);
  const message = report.status === "ready" ? "All checked services reachable" : "One or more dependencies unavailable";
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/system");
  await expect(page.getByRole("heading", { name: "Service Status" })).toBeVisible();
  await expect(page.locator("main").getByRole("status")).toHaveText(message);
  for (const service of ["postgres", "qdrant", "ollama"]) {
    await expect(page.getByTestId(`service-${service}`)).toContainText(report.checks[service].status === "ok" ? "Connected" : "Unavailable");
  }
  await page.getByRole("button", { name: "Check again" }).click();
  await expect(page.locator("main").getByRole("status")).toHaveText(message);
  expect(errors).toEqual([]);
});

test("all foundation dependencies are reachable", async ({ request }) => {
  const health = await request.get("/api/health");
  expect(health.status()).toBe(200);
  expect((await health.json()).status).toBe("ready");
});

test("connection failure is visible and refresh recovers", async ({ page, request }) => {
  const health = await request.get("/api/health");
  const report = await health.json();
  expect(["ready", "degraded"]).toContain(report.status);
  // Explicit UI failure simulation, not evidence of a real integration.
  await page.route("**/api/health", route => route.fulfill({
    status: 503, contentType: "application/json", body: JSON.stringify({ status: "unavailable" }),
  }));
  await page.goto("/system");
  await expect(page.locator("main").getByRole("status")).toHaveText("Backend unavailable");
  await page.unroute("**/api/health");
  await page.getByRole("button", { name: "Check again" }).click();
  await expect(page.locator("main").getByRole("status")).toHaveText(report.status === "ready" ? "All checked services reachable" : "One or more dependencies unavailable");
});

