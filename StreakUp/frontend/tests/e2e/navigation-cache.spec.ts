import { expect, test } from "@playwright/test";

function token(): string {
  const header = Buffer.from("{}").toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: "1", exp: Math.floor(Date.now() / 1000) + 3600 })).toString("base64url");
  return `${header}.${payload}.test`;
}

test("returning to Habits restores scroll and reuses recent data", async ({ page }) => {
  const accessToken = token();
  await page.context().addCookies([{ name: "streakup_access_token", value: accessToken, domain: "localhost", path: "/" }]);
  await page.addInitScript(({ accessToken }) => {
    window.sessionStorage.setItem("access_token", accessToken);
    window.localStorage.setItem("user", JSON.stringify({ id: 1, username: "test", email: "test@example.com", role: "user" }));
  }, { accessToken });

  let habitsRequests = 0;
  const habits = Array.from({ length: 24 }, (_, index) => ({
    id: index + 1, user_id: 1, catalog_habit_id: null, name: `Hábito ${index + 1}`,
    icon: "Flame", section: "fire", difficulty: "facil", validation_type: "foto",
    frequency: "daily", target_duration: null, target_quantity: null, target_unit: null,
    active: true, xp_base: 10,
  }));
  await page.route("**/api/habits", async (route) => {
    habitsRequests += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(habits) });
  });
  await page.route("**/api/checkins/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.route("**/api/social/groups", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.route("**/api/stats/summary", (route) => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ streak: 0, today_completed: 0, today_total: 0, completion_rate: 0, total_xp: 0, level: 1, validations_today: 0 }),
  }));

  await page.goto("/habits");
  await expect(page.getByText("Hábito 24")).toBeAttached();
  const main = page.locator("main#main-content");
  await main.evaluate((element) => { element.scrollTop = 600; });
  await expect.poll(() => main.evaluate((element) => element.scrollTop)).toBeGreaterThan(400);

  await page.getByRole("navigation", { name: "Navegación principal" }).getByRole("link", { name: "Inicio" }).evaluate((element) => (element as HTMLElement).click());
  await expect(page).toHaveURL(/:\d+\/$/);
  await page.getByRole("navigation", { name: "Navegación principal" }).getByRole("link", { name: "Hábitos" }).evaluate((element) => (element as HTMLElement).click());
  await expect(page).toHaveURL(/\/habits$/);
  await expect.poll(() => main.evaluate((element) => element.scrollTop)).toBeGreaterThan(400);
  expect(habitsRequests).toBe(1);
});
