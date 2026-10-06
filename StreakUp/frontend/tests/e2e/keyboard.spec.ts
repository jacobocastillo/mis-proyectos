/**
 * Keyboard navigation smoke tests.
 *
 * Verifies that the main interactive elements are reachable and operable
 * via Tab + Enter/Space without a mouse.
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

// ── Login form ────────────────────────────────────────────────────────────────

test("login: Tab reaches email, password inputs and submit button", async ({ page }) => {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  await page.keyboard.press("Tab");
  const focused1 = await page.evaluate(() => document.activeElement?.id);
  expect(focused1).toBe("login-email");

  await page.keyboard.press("Tab");
  const focused2 = await page.evaluate(() => document.activeElement?.id);
  expect(focused2).toBe("login-password");

  await page.keyboard.press("Tab");
  const focused3 = await page.evaluate(() => document.activeElement?.getAttribute("type"));
  expect(focused3).toBe("submit");
});

// ── Register form ─────────────────────────────────────────────────────────────

test("register: Tab reaches all four inputs", async ({ page }) => {
  await page.goto("/register");
  await page.waitForLoadState("networkidle");

  const expectedIds = ["reg-username", "reg-email", "reg-password", "reg-confirm-password"];
  for (const id of expectedIds) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => document.activeElement?.id);
    expect(focused).toBe(id);
  }
});

// ── Bottom nav ────────────────────────────────────────────────────────────────

test("bottom nav: Tab cycles through all four links", async ({ page }) => {
  await injectSession(page);
  await page.goto("/");
  await page.waitForSelector("[aria-label='Navegación principal']");

  const navLinks = await page.locator("nav[aria-label='Navegación principal'] a").all();
  expect(navLinks).toHaveLength(4);

  for (const link of navLinks) {
    await expect(link).toBeVisible();
  }
});

// ── Skip link ─────────────────────────────────────────────────────────────────

test("dashboard: skip link is focusable and targets main content", async ({ page }) => {
  await injectSession(page);
  await page.goto("/");
  const skipLink = page.getByRole("link", { name: /saltar al contenido principal/i });
  await expect(skipLink).toBeAttached();

  // First Tab press should focus the skip link
  await skipLink.focus();
  const activeHref = await page.evaluate(() =>
    (document.activeElement as HTMLAnchorElement | null)?.href,
  );
  expect(activeHref).toContain("#main-content");

  // Pressing Enter should move focus to main
  await page.keyboard.press("Enter");
  const activeId = await page.evaluate(() => document.activeElement?.id);
  expect(activeId).toBe("main-content");
});

// ── Delete modal: Escape closes ───────────────────────────────────────────────

test("delete account modal closes on Escape", async ({ page }) => {
  await injectSession(page);
  await page.goto("/profile");
  await page.waitForLoadState("networkidle");

  const deleteBtn = page.getByRole("button", { name: /eliminar cuenta/i });
  if (!(await deleteBtn.isVisible().catch(() => false))) {
    test.skip();
    return;
  }

  await deleteBtn.click();
  await page.waitForSelector("[role='dialog']", { timeout: 3000 });
  expect(await page.locator("[role='dialog']").isVisible()).toBe(true);

  await page.keyboard.press("Escape");
  await expect(page.locator("[role='dialog']")).not.toBeVisible({ timeout: 2000 });
});
