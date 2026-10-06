/**
 * Overflow tests — no horizontal scrollbar at any target viewport.
 *
 * Tests are parameterized per viewport via Playwright projects defined in
 * playwright.config.ts (mobile, tablet, desktop, landscape).
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

async function hasHorizontalOverflow(page: import("@playwright/test").Page): Promise<boolean> {
  return page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth;
  });
}

const PUBLIC_ROUTES = ["/login", "/register"];
const DASHBOARD_ROUTES = ["/", "/habits", "/stats", "/profile"];

for (const path of PUBLIC_ROUTES) {
  test(`no horizontal overflow — ${path}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    expect(await hasHorizontalOverflow(page)).toBe(false);
  });
}

for (const path of DASHBOARD_ROUTES) {
  test(`no horizontal overflow — ${path} (dashboard)`, async ({ page }) => {
    await injectSession(page);
    await page.goto(path);
    await page.waitForSelector("[aria-label='Cargando datos']", { state: "hidden", timeout: 8000 }).catch(() => null);
    await page.waitForLoadState("networkidle");
    expect(await hasHorizontalOverflow(page)).toBe(false);
  });
}
