import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { register } from "@/services/auth/authService";
import { installBrowserTestEnv, restoreBrowserTestEnv } from "../test-utils";

// Requirement mapping:
// RF-01: Users can register an account from the frontend auth service.

beforeEach(installBrowserTestEnv);
afterEach(restoreBrowserTestEnv);

test("RF-01 registration posts user credentials and opens a session", async () => {
  globalThis.fetch = async (input, init) => {
    assert.equal(input, "/api/auth/register");
    assert.equal(init?.method, "POST");
    assert.deepEqual(JSON.parse(String(init?.body)), {
      username: "rf_user",
      email: "rf@example.com",
      password: "rf-password",
    });

    return new Response(
      JSON.stringify({
        message: "User registered successfully.",
        access_token: "access-test",
        refresh_token: "refresh-test",
        user: {
          id: 7,
          username: "rf_user",
          email: "rf@example.com",
          role: "user",
          created_at: "2026-01-01T00:00:00Z",
        },
      }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    );
  };

  const result = await register({
    username: "rf_user",
    email: "rf@example.com",
    password: "rf-password",
  });

  assert.equal(result.user.email, "rf@example.com");
  assert.equal(result.user.username, "rf_user");
  assert.equal(result.access_token, "access-test");
  assert.equal(result.refresh_token, "refresh-test");
});
