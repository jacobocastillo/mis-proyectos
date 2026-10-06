/**
 * Accessibility audit — axe-core scans on all main pages.
 *
 * Dashboard pages require authentication. We inject a fake session into
 * sessionStorage + localStorage before navigation so the client-side guard
 * lets us through. The middleware cookie check is bypassed by setting the
 * auth cookie via `page.context().addCookies()`.
 *
 * Run against the Next.js dev server: `npx playwright test tests/e2e/a11y.spec.ts`
 */

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// ── Helpers ──────────────────────────────────────────────────────────────────

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
    {
      name: "streakup_access_token",
      value: token,
      domain: "localhost",
      path: "/",
    },
  ]);

  await page.addInitScript(
    ({ token, user }) => {
      window.sessionStorage.setItem("access_token", token);
      window.localStorage.setItem("user", JSON.stringify(user));
    },
    { token, user: FAKE_USER },
  );
}

// ── Public pages ──────────────────────────────────────────────────────────────

test.describe("Login page — axe scan", () => {
  test("no critical/serious violations", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    const violations = results.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact ?? ""),
    );
    expect(violations, JSON.stringify(violations, null, 2)).toHaveLength(0);
  });
});

test.describe("Register page — axe scan", () => {
  test("no critical/serious violations", async ({ page }) => {
    await page.goto("/register");
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    const violations = results.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact ?? ""),
    );
    expect(violations, JSON.stringify(violations, null, 2)).toHaveLength(0);
  });
});

// ── Dashboard pages (require fake session) ────────────────────────────────────

const DASHBOARD_ROUTES = [
  { name: "Home", path: "/" },
  { name: "Habits", path: "/habits" },
  { name: "Stats", path: "/stats" },
  { name: "Profile", path: "/profile" },
];

for (const route of DASHBOARD_ROUTES) {
  test.describe(`${route.name} page — axe scan`, () => {
    test("no critical/serious violations", async ({ page }) => {
      await injectSession(page);
      await page.goto(route.path);
      // Wait for spinner to disappear (session check complete)
      await page.waitForSelector("[aria-label='Cargando datos']", { state: "hidden", timeout: 8000 }).catch(() => null);
      await page.waitForLoadState("networkidle");

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .exclude("[data-axe-ignore]")
        .analyze();

      const violations = results.violations.filter((v) =>
        ["critical", "serious"].includes(v.impact ?? ""),
      );
      expect(violations, JSON.stringify(violations, null, 2)).toHaveLength(0);
    });
  });
}

// ── Delete account modal ─────────────────────────────────────────────────────

test.describe("Delete account modal — axe scan", () => {
  test("no critical/serious violations when open", async ({ page }) => {
    await injectSession(page);
    await page.goto("/profile");
    await page.waitForLoadState("networkidle");

    // Open the modal via the delete account button
    const deleteBtn = page.getByRole("button", { name: /eliminar cuenta/i });
    if (await deleteBtn.isVisible().catch(() => false)) {
      await deleteBtn.click();
      await page.waitForSelector("[role='dialog']", { timeout: 3000 }).catch(() => null);

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .analyze();

      const violations = results.violations.filter((v) =>
        ["critical", "serious"].includes(v.impact ?? ""),
      );
      expect(violations, JSON.stringify(violations, null, 2)).toHaveLength(0);
    } else {
      test.skip();
    }
  });
});

// ── Network status banner ────────────────────────────────────────────────────

test.describe("Offline banner — axe scan", () => {
  test("no critical/serious violations when offline", async ({ page }) => {
    await injectSession(page);

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Simulate offline state after the app shell is loaded.
    const client = await page.context().newCDPSession(page);
    await client.send("Network.enable");
    await client.send("Network.emulateNetworkConditions", {
      offline: true,
      latency: 0,
      downloadThroughput: 0,
      uploadThroughput: 0,
    });
    await page.evaluate(() => window.dispatchEvent(new Event("offline")));
    await page.waitForTimeout(500);

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    const violations = results.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact ?? ""),
    );
    expect(violations, JSON.stringify(violations, null, 2)).toHaveLength(0);
  });
});
