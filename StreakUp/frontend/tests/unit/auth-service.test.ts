import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import {
  getSession,
  hasSavedSession,
  login,
  register,
  saveSession,
  clearSession,
  logoutAndClear,
} from "@/services/auth/authService";
import { AUTH_COOKIE_NAME } from "@/services/auth/session";
import { setCredentialStore, resetCredentialStore } from "@/services/auth/credentialProvider";
import { DB_KEYS } from "@/services/storage/offlineDb";

const originalFetch = globalThis.fetch;
const originalNavigator = globalThis.navigator;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;

function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
}

function createValidAccessToken(overrides: Record<string, unknown> = {}): string {
  return buildJwt({
    sub: "7",
    exp: Math.floor(Date.now() / 1000) + 3600,
    ...overrides,
  });
}

function createStorage(): Storage {
  const store = new Map<string, string>();

  return {
    clear() {
      store.clear();
    },
    getItem(key) {
      return store.get(key) ?? null;
    },
    key(index) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
    removeItem(key) {
      store.delete(key);
    },
    setItem(key, value) {
      store.set(key, String(value));
    },
  };
}

function createWindow() {
  return {
    localStorage: createStorage(),
    sessionStorage: createStorage(),
    location: {
      href: "",
    },
  };
}

function createDocument() {
  let cookie = "";

  return {
    get cookie() {
      return cookie;
    },
    set cookie(value: string) {
      cookie = value;
    },
  };
}

beforeEach(() => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "";

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: createWindow(),
  });

  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: createDocument(),
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  resetCredentialStore();

  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: originalNavigator,
  });

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });

  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: originalDocument,
  });

  if (originalOfflineMode === undefined) {
    delete process.env.NEXT_PUBLIC_OFFLINE_MODE;
  } else {
    process.env.NEXT_PUBLIC_OFFLINE_MODE = originalOfflineMode;
  }
});

// 🔐 Datos fake para evitar detección de secretos
const TEST_EMAIL = "test@example.com";
const TEST_PASSWORD = "test_password";

test("saveSession and getSession round-trip", () => {
  const accessToken = createValidAccessToken();
  saveSession({
    access_token: accessToken,
    refresh_token: "saved-refresh",
    user: {
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
      created_at: "2026-03-27T00:00:00Z",
    },
  });

  const session = getSession();
  assert.notEqual(session, null);
  assert.equal(session?.accessToken, accessToken);
  assert.equal(session?.user.email, TEST_EMAIL);
  assert.match(document.cookie, new RegExp(`^${AUTH_COOKIE_NAME}=`));
});

test("clearSession removes all stored auth data", () => {
  saveSession({
    access_token: createValidAccessToken(),
    refresh_token: "saved-refresh",
    user: {
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
      created_at: "2026-03-27T00:00:00Z",
    },
  });

  clearSession();

  assert.equal(getSession(), null);
  // Tokens are in the credential store (sessionStorage), not localStorage
  assert.equal(window.sessionStorage.getItem("access_token"), null);
  assert.equal(window.sessionStorage.getItem("refresh_token"), null);
  assert.equal(window.localStorage.getItem("access_token"), null);
  assert.equal(window.localStorage.getItem("refresh_token"), null);
  assert.equal(window.localStorage.getItem("user"), null);
  assert.match(document.cookie, new RegExp(`^${AUTH_COOKIE_NAME}=;`));
});

test("hasSavedSession returns false when no session exists", () => {
  assert.equal(hasSavedSession(), false);
});

test("hasSavedSession returns true when session exists", () => {
  saveSession({
    access_token: createValidAccessToken(),
    refresh_token: "saved-refresh",
    user: {
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
      created_at: "2026-03-27T00:00:00Z",
    },
  });

  assert.equal(hasSavedSession(), true);
});

test("hasSavedSession returns false for malformed tokens and clears storage", () => {
  window.sessionStorage.setItem("access_token", "not-a-jwt");
  window.localStorage.setItem(
    "user",
    JSON.stringify({
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
    }),
  );

  assert.equal(hasSavedSession(), false);
  assert.equal(window.sessionStorage.getItem("access_token"), null);
  assert.equal(window.localStorage.getItem("user"), null);
});

test("hasSavedSession returns false for expired tokens", () => {
  window.sessionStorage.setItem(
    "access_token",
    createValidAccessToken({ exp: Math.floor(Date.now() / 1000) - 60 }),
  );
  window.localStorage.setItem(
    "user",
    JSON.stringify({
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
    }),
  );

  assert.equal(hasSavedSession(), false);
});

test("register does not block when navigator.onLine is false", async () => {
  let fetchCalls = 0;

  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { onLine: false },
  });

  globalThis.fetch = async (input, init) => {
    fetchCalls += 1;

    assert.equal(input, "/api/auth/register");
    assert.equal(init?.method, "POST");

    return new Response(
      JSON.stringify({
        message: "User registered successfully.",
        user: {
          id: 7,
          username: "alice",
          email: TEST_EMAIL,
          role: "user",
          created_at: "2026-03-27T00:00:00Z",
        },
      }),
      {
        status: 201,
        headers: { "Content-Type": "application/json" },
      },
    );
  };

  const result = await register({
    username: "alice",
    email: TEST_EMAIL,
    password: TEST_PASSWORD,
  });

  assert.equal(fetchCalls, 1);
  assert.equal(result.user.email, TEST_EMAIL);
});

test("register reports offline only after a real request failure", async () => {
  let fetchCalls = 0;

  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { onLine: false },
  });

  globalThis.fetch = async () => {
    fetchCalls += 1;
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(
    register({
      username: "alice",
      email: TEST_EMAIL,
      password: TEST_PASSWORD,
    }),
    (error: unknown) => {
      assert.equal(fetchCalls, 2);
      assert.equal(
        error instanceof Error ? error.message : String(error),
        "No hay conexión. El registro requiere internet.",
      );
      return true;
    },
  );
});

test("login reports offline when the backend request fails", async () => {
  let fetchCalls = 0;

  globalThis.fetch = async () => {
    fetchCalls += 1;
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(
    login({
      email: TEST_EMAIL.toUpperCase(),
      password: TEST_PASSWORD,
    }),
    (error: unknown) => {
      assert.equal(fetchCalls, 2);
      assert.ok(error instanceof Error);
      return true;
    },
  );
});

test("login with cached session fails securely when backend request throws", async () => {
  saveSession({
    access_token: "saved-access",
    refresh_token: "saved-refresh",
    user: {
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
      created_at: "2026-03-27T00:00:00Z",
    },
  });

  let fetchCalls = 0;
  globalThis.fetch = async () => {
    fetchCalls += 1;
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(
    login({
      email: TEST_EMAIL,
      password: "wrong_password",
    }),
    (error: unknown) => {
      assert.equal(fetchCalls, 2);
      assert.ok(error instanceof Error);
      assert.equal(error.message, "No hay conexión. Usa una sesión guardada previamente.");
      return true;
    },
  );
});

test("web session does not persist tokens in localStorage", () => {
  const accessToken = createValidAccessToken();
  saveSession({
    access_token: accessToken,
    refresh_token: "r-token",
    user: {
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
      created_at: "2026-03-27T00:00:00Z",
    },
  });

  // Tokens must NOT appear in localStorage
  assert.equal(window.localStorage.getItem("access_token"), null);
  assert.equal(window.localStorage.getItem("refresh_token"), null);

  // Session must still be retrievable
  const session = getSession();
  assert.notEqual(session, null);
  assert.equal(session?.accessToken, accessToken);
});

test("credential store adapter is used instead of localStorage", () => {
  const captured: Record<string, string> = {};
  const mockStore = {
    get: (key: string) => captured[key] ?? null,
    set: (key: string, value: string) => { captured[key] = value; },
    remove: (key: string) => { delete captured[key]; },
    clear: (keys: string[]) => { keys.forEach((k) => delete captured[k]); },
  };

  setCredentialStore(mockStore);

  const accessToken = createValidAccessToken();
  saveSession({
    access_token: accessToken,
    refresh_token: "r-token",
    user: {
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
      created_at: "2026-03-27T00:00:00Z",
    },
  });

  // Tokens routed through the injected store, not localStorage
  assert.equal(captured["access_token"], accessToken);
  assert.equal(captured["refresh_token"], "r-token");
  assert.equal(window.localStorage.getItem("access_token"), null);
  assert.equal(window.localStorage.getItem("refresh_token"), null);
});

test("logoutAndClear clears session credentials and all offline caches", async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ message: "Logged out." }), { status: 200, headers: { "Content-Type": "application/json" } });

  saveSession({
    access_token: createValidAccessToken(),
    refresh_token: "r-token",
    user: {
      id: 7,
      username: "user_test",
      email: TEST_EMAIL,
      role: "user",
      created_at: "2026-03-27T00:00:00Z",
    },
  });

  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([{ id: -1 }]));
  window.localStorage.setItem(DB_KEYS.pendingOps, JSON.stringify([{ id: "op1" }]));

  await logoutAndClear();

  assert.equal(getSession(), null);
  assert.equal(window.sessionStorage.getItem("access_token"), null);
  // Offline caches must be cleared
  assert.deepEqual(JSON.parse(window.localStorage.getItem(DB_KEYS.habits) ?? "[]"), []);
  assert.deepEqual(JSON.parse(window.localStorage.getItem(DB_KEYS.pendingOps) ?? "[]"), []);
});
