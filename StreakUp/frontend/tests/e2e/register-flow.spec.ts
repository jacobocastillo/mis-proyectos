import { expect, test } from "@playwright/test";

function token(): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: "42", exp: Math.floor(Date.now() / 1000) + 3600 })).toString("base64url");
  return `${header}.${payload}.test`;
}

test("direct registration link can return to login", async ({ page }) => {
  await page.goto("/register");
  await page.getByRole("link", { name: "Volver a iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
});

test("registration shows live length and opens an authenticated session", async ({ page }) => {
  let registrationRequests = 0;
  const accessToken = token();
  await page.route("**/api/auth/register", async (route) => {
    registrationRequests += 1;
    await new Promise((resolve) => setTimeout(resolve, 150));
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        message: "User registered successfully.",
        access_token: accessToken,
        refresh_token: "refresh-test",
        user: { id: 42, username: "testuser", email: "test@example.com", role: "user", created_at: "2026-01-01T00:00:00Z" },
      }),
    });
  });

  await page.goto("/register");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("#password-help")).toContainText("0/8 caracteres mínimos");
  await expect(page.getByRole("button", { name: "Iniciar sesión" })).toHaveCount(0);

  const password = page.locator("#reg-password");
  await password.fill("12345");
  await expect(page.locator("#password-help")).toContainText("5/8 caracteres mínimos");
  await password.fill("12345678");
  await expect(page.locator("#password-help")).toContainText("8/8 caracteres mínimos · Longitud mínima cumplida");
  await password.fill("123456789");
  await expect(page.locator("#password-help")).toContainText("9/8 caracteres mínimos · Longitud mínima cumplida");
  await password.fill("1234");
  await expect(page.locator("#password-help")).toContainText("4/8 caracteres mínimos");
  await password.fill("12345678");

  await page.locator("#reg-username").fill("testuser");
  await page.locator("#reg-email").fill("test@example.com");
  await page.locator("#reg-confirm-password").fill("12345678");
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page.getByRole("button", { name: "Creando cuenta…" })).toBeDisabled();
  await expect(page).toHaveURL(/:\d+\/$/);
  expect(registrationRequests).toBe(1);
  expect(await page.evaluate(() => window.sessionStorage.getItem("access_token"))).toBe(accessToken);
});

test("registration signs in automatically with the existing backend response", async ({ page }) => {
  const accessToken = token();
  let loginRequests = 0;
  const user = { id: 43, username: "legacyuser", email: "legacy@example.com", role: "user", created_at: "2026-01-01T00:00:00Z" };
  await page.route("**/api/auth/register", (route) => route.fulfill({
    status: 201,
    contentType: "application/json",
    body: JSON.stringify({ message: "User registered successfully.", user }),
  }));
  await page.route("**/api/auth/login", (route) => {
    loginRequests += 1;
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: accessToken, refresh_token: "refresh-test", user }),
    });
  });

  await page.goto("/register");
  await page.waitForLoadState("networkidle");
  await page.locator("#reg-username").fill(user.username);
  await page.locator("#reg-email").fill(user.email);
  await page.locator("#reg-password").fill("12345678");
  await page.locator("#reg-confirm-password").fill("12345678");
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page).toHaveURL(/:\d+\/$/);
  expect(loginRequests).toBe(1);
  expect(await page.evaluate(() => window.sessionStorage.getItem("access_token"))).toBe(accessToken);
});
