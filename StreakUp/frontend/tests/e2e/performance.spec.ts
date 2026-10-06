import { test, expect, type Page } from "@playwright/test";

const USABLE_RENDER_BUDGET_MS = 3_000;

function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.fake-sig`;
}

function validAccessToken(): string {
  return buildJwt({ sub: "1", exp: Math.floor(Date.now() / 1000) + 3600 });
}

const FAKE_USER = {
  id: 1,
  username: "testuser",
  email: "test@example.com",
  role: "user",
  created_at: "2026-01-01T00:00:00Z",
};

async function injectSession(page: Page) {
  const token = validAccessToken();

  await page.context().addCookies([
    { name: "streakup_access_token", value: token, domain: "localhost", path: "/" },
  ]);
  await page.addInitScript(
    ({ token, user }) => {
      window.sessionStorage.setItem("access_token", token);
      window.localStorage.setItem("user", JSON.stringify(user));
    },
    { token, user: FAKE_USER },
  );
}

async function mockApi(page: Page) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    const json = (body: unknown) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });

    if (path === "/api/users/me") {
      return json(FAKE_USER);
    }
    if (path === "/api/habits" || path === "/api/checkins/today") {
      return json([
        {
          id: 1,
          user_id: 1,
          catalog_habit_id: 1,
          name: "Tomar agua",
          icon: "Flame",
          habit_type: "boolean",
          frequency: "daily",
          section: "fire",
          target_duration: null,
          target_quantity: null,
          target_unit: null,
          pomodoro_enabled: false,
          checked_today: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ]);
    }
    if (path === "/api/stats/summary") {
      return json({
        streak: 4,
        today_completed: 1,
        today_total: 3,
        completion_rate: 33,
        habits_count: 3,
        total_xp: 120,
        level: 1,
        validations_today: 0,
      });
    }
    if (path === "/api/stats/xp") {
      return json({
        total_xp: 120,
        level: 1,
        xp_in_level: 120,
        xp_for_next_level: 250,
        progress_pct: 48,
      });
    }
    if (path === "/api/stats/detailed") {
      return json({
        records: { longest_streak: 4, best_day: 3, current_streak: 4, active_days: 6 },
        validations: { total_successful: 0, total_attempts: 0, success_rate: 0 },
      });
    }
    if (path === "/api/achievements") {
      return json([]);
    }
    if (path === "/api/telemetry/errors") {
      return route.fulfill({ status: 202, contentType: "application/json", body: '{"status":"accepted"}' });
    }

    return json({});
  });
}

async function expectUsableWithinBudget(page: Page, path: string, selector: string) {
  await injectSession(page);
  await mockApi(page);

  // Warm Next dev-server route compilation before measuring the user-facing budget.
  await page.goto(path);
  await page.locator(selector).first().waitFor({ state: "visible", timeout: 10_000 });

  const startedAt = Date.now();
  await page.reload();
  await page.locator(selector).first().waitFor({ state: "visible", timeout: USABLE_RENDER_BUDGET_MS });
  const elapsed = Date.now() - startedAt;

  expect(elapsed).toBeLessThanOrEqual(USABLE_RENDER_BUDGET_MS);
}

test.describe("@performance RNF-02 budgets", () => {
  test("home reaches usable state within the RNF-02 budget", async ({ page }) => {
    await expectUsableWithinBudget(page, "/", "text=Tomar agua");
  });

  test("habits reaches usable state within the RNF-02 budget", async ({ page }) => {
    await expectUsableWithinBudget(page, "/habits", "text=Tomar agua");
  });

  test("profile reaches usable state within the RNF-02 budget", async ({ page }) => {
    await expectUsableWithinBudget(page, "/profile", "text=testuser");
  });
});
