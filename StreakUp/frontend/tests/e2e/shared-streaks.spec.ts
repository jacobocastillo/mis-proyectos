/**
 * E2E tests — shared streak groups (social feature).
 *
 * Mocks API responses so no real backend is required.
 * Run: `npx playwright test tests/e2e/shared-streaks.spec.ts`
 */

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

const MOCK_GROUPS = [
  {
    id: 1,
    name: "Equipo Mañanero",
    invite_code: "ABC123",
    owner_user_id: 1,
    habit_id: 7,
    habit_name: "Leer",
    max_participants: 3,
    member_count: 3,
    start_date: null,
    duration_days: null,
    end_date: null,
    group_status: "active",
    winner_user_id: null,
    shared_streak: { current: 2, today_completed_members: 1, required_members: 3, ready: false },
    created_at: "2026-01-01T00:00:00Z",
    members: [
      { user_id: 1, username: "testuser", status: "active", share_progress: true, joined_at: null, lost_at: null, today_completed: true, completed_days: 2 },
      { user_id: 2, username: "amigo1", status: "active", share_progress: true, joined_at: null, lost_at: null, today_completed: false, completed_days: 1 },
      { user_id: 3, username: "amigo2", status: "active", share_progress: false, joined_at: null, lost_at: null, today_completed: false, completed_days: 0 },
    ],
  },
];

async function mockSocialApi(page: import("@playwright/test").Page) {
  await page.route("**/api/habits", (route) => route.fulfill({ json: [{ id: 7, name: "Leer" }] }));
  await page.route("**/api/social/groups", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: MOCK_GROUPS });
    } else if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as { name?: string };
      await route.fulfill({
        status: 201,
        json: {
          ...MOCK_GROUPS[0],
          id: 99,
          name: body?.name ?? "Nuevo Grupo",
          invite_code: "NEW999",
          member_count: 1,
          members: [MOCK_GROUPS[0].members[0]],
        },
      });
    } else {
      await route.continue();
    }
  });

  await page.route("**/api/social/groups/join", async (route) => {
    await route.fulfill({ status: 200, json: { ...MOCK_GROUPS[0], id: 2, name: "Equipo Invitado" } });
  });

  await page.route("**/api/social/groups/1", async (route) => {
    await route.fulfill({ json: MOCK_GROUPS[0] });
  });
}

test.describe("Social — group list", () => {
  test("shows existing groups", async ({ page }) => {
    await injectSession(page);
    await mockSocialApi(page);
    await page.goto("/social");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Equipo Mañanero")).toBeVisible({ timeout: 8000 });
  });
});

test.describe("Social — create group", () => {
  test("creates a new group and shows it in the list", async ({ page }) => {
    await injectSession(page);
    await mockSocialApi(page);
    await page.goto("/social");
    await page.waitForLoadState("networkidle");

    await page.getByPlaceholder("Nombre del reto").fill("Grupo de Prueba");
    await page.getByRole("combobox", { name: "Seleccionar hábito" }).selectOption("7");
    await page.getByRole("button", { name: "Crear reto" }).click();

    await expect(page.getByText("Grupo de Prueba")).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Social — join group", () => {
  test("joins an existing group with invite code", async ({ page }) => {
    await injectSession(page);
    await mockSocialApi(page);
    await page.goto("/social");
    await page.waitForLoadState("networkidle");

    await page.getByPlaceholder("Código de invitación").fill("ABC123");
    await page.getByRole("button", { name: "Unirme al grupo" }).click();

    await expect(page.getByText("Equipo Invitado")).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Social — group detail members", () => {
  test("members are visible in group detail", async ({ page }) => {
    await injectSession(page);
    await mockSocialApi(page);
    await page.goto("/social");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("amigo1")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("amigo2")).toBeVisible({ timeout: 5000 });
  });
});
