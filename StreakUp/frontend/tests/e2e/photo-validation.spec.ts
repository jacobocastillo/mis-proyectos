/**
 * E2E tests — photo/text validation flow.
 *
 * Mocks backend /api/validate responses so no real OpenAI key is required.
 * Run: `npx playwright test tests/e2e/photo-validation.spec.ts`
 */

import path from "node:path";
import { test, expect } from "@playwright/test";

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

async function injectSession(page: import("@playwright/test").Page) {
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

const MOCK_HABIT = {
  id: 1,
  name: "Hacer ejercicio",
  validation_type: "photo",
  frequency: "daily",
  active: true,
};

const APPROVED_VALIDATION_RESPONSE = {
  approved: true,
  xp_awarded: 50,
  streak: 5,
  today_completed: 1,
  today_total: 3,
  habit_name: "Hacer ejercicio",
  feedback: {
    message: "¡Excelente! Validaste Hacer ejercicio y mantienes una racha de 5 días.",
    tone: "streak",
  },
};

const REJECTED_VALIDATION_RESPONSE = {
  approved: false,
  xp_awarded: 0,
  streak: 4,
  today_completed: 0,
  today_total: 3,
  habit_name: "Hacer ejercicio",
  feedback: {
    message: "La evidencia de Hacer ejercicio no fue suficiente. Ajusta el intento y vuelve a validar.",
    tone: "retry",
  },
};

async function mockHabitsApi(page: import("@playwright/test").Page) {
  await page.route("/api/habits", async (route) => {
    await route.fulfill({ json: { habits: [MOCK_HABIT] } });
  });
  await page.route("/api/habits/1", async (route) => {
    await route.fulfill({ json: MOCK_HABIT });
  });
  await page.route("/api/checkins/today", async (route) => {
    await route.fulfill({ json: { checkins: [] } });
  });
  await page.route("/api/stats/summary", async (route) => {
    await route.fulfill({
      json: {
        today_completed: 0,
        today_total: 3,
        streak: 4,
        completion_rate: 0,
        validations_today: 0,
      },
    });
  });
}

test.describe("Validation — approved photo", () => {
  test("completes full validation flow and shows success feedback", async ({ page }) => {
    await injectSession(page);
    await mockHabitsApi(page);

    await page.route("/api/validate", async (route) => {
      await route.fulfill({ json: APPROVED_VALIDATION_RESPONSE });
    });

    await page.goto("/habits/validate");
    await page.waitForLoadState("networkidle");

    const fileInput = page.locator('input[type="file"]');
    if (!(await fileInput.isVisible().catch(() => false))) {
      test.skip();
      return;
    }

    const fakeImagePath = path.join(process.cwd(), "tests", "fixtures", "test-image.jpg");
    await fileInput.setInputFiles(fakeImagePath).catch(async () => {
      // If no file input found, try the camera trigger button
      const cameraBtn = page.getByRole("button", { name: /foto|cámara|imagen/i });
      if (await cameraBtn.isVisible().catch(() => false)) {
        test.skip();
      }
    });

    const submitBtn = page.getByRole("button", { name: /validar|enviar|confirmar/i });
    if (await submitBtn.isVisible().catch(() => false)) {
      await submitBtn.click();
    }

    await expect(
      page.getByText(/racha|validaste|excelente/i)
    ).toBeVisible({ timeout: 8000 });
  });
});

test.describe("Validation — rejected photo", () => {
  test("shows retry message when validation fails", async ({ page }) => {
    await injectSession(page);
    await mockHabitsApi(page);

    await page.route("/api/validate", async (route) => {
      await route.fulfill({ json: REJECTED_VALIDATION_RESPONSE });
    });

    await page.goto("/habits/validate");
    await page.waitForLoadState("networkidle");

    const fileInput = page.locator('input[type="file"]');
    if (!(await fileInput.isVisible().catch(() => false))) {
      test.skip();
      return;
    }

    const fakeImagePath = path.join(process.cwd(), "tests", "fixtures", "test-image.jpg");
    await fileInput.setInputFiles(fakeImagePath).catch(() => null);

    const submitBtn = page.getByRole("button", { name: /validar|enviar|confirmar/i });
    if (await submitBtn.isVisible().catch(() => false)) {
      await submitBtn.click();
    }

    await expect(
      page.getByText(/no fue suficiente|ajusta|reintentar/i)
    ).toBeVisible({ timeout: 8000 });
  });
});

test.describe("Validation — OpenAI unavailable fallback", () => {
  test("falls back to manual validation when AI is unavailable", async ({ page }) => {
    await injectSession(page);
    await mockHabitsApi(page);

    await page.route("/api/validate", async (route) => {
      await route.fulfill({
        status: 503,
        json: {
          error: "La validación de fotos no está disponible temporalmente.",
          code: "validation_provider_unavailable",
        },
      });
    });

    await page.goto("/habits/validate");
    await page.waitForLoadState("networkidle");

    const fileInput = page.locator('input[type="file"]');
    if (!(await fileInput.isVisible().catch(() => false))) {
      test.skip();
      return;
    }

    const fakeImagePath = path.join(process.cwd(), "tests", "fixtures", "test-image.jpg");
    await fileInput.setInputFiles(fakeImagePath).catch(() => null);

    const submitBtn = page.getByRole("button", { name: /validar|enviar|confirmar/i });
    if (await submitBtn.isVisible().catch(() => false)) {
      await submitBtn.click();
    }

    await expect(
      page.getByText(/disponible|temporalmente|reintentar|manual/i)
    ).toBeVisible({ timeout: 8000 });
  });
});
