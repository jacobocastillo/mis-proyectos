import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { Capacitor } from "@capacitor/core";

import {
  AppError,
  OfflineModeError,
  apiRequest,
  isAppErrorCode,
  shouldUseOfflineFallback,
} from "@/services/api/client";
import { isOfflineModeActive } from "@/services/config/runtime";
import { resetCredentialStore } from "@/services/auth/credentialProvider";

const originalFetch = globalThis.fetch;
const originalNavigator = globalThis.navigator;
const originalWindow = globalThis.window;
const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;
const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_URL;
const originalNodeEnv = process.env.NODE_ENV;
const originalIsNativePlatform = Capacitor.isNativePlatform;
const mutableEnv = process.env as Record<string, string | undefined>;

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

beforeEach(() => {
  mutableEnv.NEXT_PUBLIC_OFFLINE_MODE = "";
  mutableEnv.NEXT_PUBLIC_API_URL = "";
  mutableEnv.NODE_ENV = "test";

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: createWindow(),
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  resetCredentialStore();
  Capacitor.isNativePlatform = originalIsNativePlatform;
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: originalNavigator,
  });
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });

  if (originalOfflineMode === undefined) {
    delete mutableEnv.NEXT_PUBLIC_OFFLINE_MODE;
  } else {
    mutableEnv.NEXT_PUBLIC_OFFLINE_MODE = originalOfflineMode;
  }

  if (originalApiBaseUrl === undefined) {
    delete mutableEnv.NEXT_PUBLIC_API_URL;
  } else {
    mutableEnv.NEXT_PUBLIC_API_URL = originalApiBaseUrl;
  }

  if (originalNodeEnv === undefined) {
    delete mutableEnv.NODE_ENV;
    return;
  }

  mutableEnv.NODE_ENV = originalNodeEnv;
});

test("isOfflineModeActive ignores navigator.onLine", () => {
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { onLine: false },
  });

  assert.equal(isOfflineModeActive(), false);
});

test("apiRequest still attempts fetch when navigator reports offline", async () => {
  let fetchCalls = 0;

  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { onLine: false },
  });

  globalThis.fetch = async (input, init) => {
    fetchCalls += 1;

    assert.equal(input, "/api/habits");
    assert.equal(init?.method, "GET");

    return new Response(JSON.stringify([{ id: 1 }]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const result = await apiRequest<Array<{ id: number }>>({
    path: "/api/habits",
    method: "GET",
  });

  assert.equal(fetchCalls, 1);
  assert.deepEqual(result, [{ id: 1 }]);
});

test("apiRequest adds the bearer token when a saved session exists", async () => {
  window.sessionStorage.setItem("access_token", "saved-access");

  globalThis.fetch = async (_input, init) => {
    assert.equal(init?.headers instanceof Headers, false);
    assert.deepEqual(init?.headers, {
      "Content-Type": "application/json",
      Authorization: "Bearer saved-access",
    });

    return new Response(JSON.stringify([{ id: 1 }]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  await apiRequest<Array<{ id: number }>>({
    path: "/api/habits",
    method: "GET",
  });
});

test("apiRequest uses OfflineModeError only for explicit forced offline mode", async () => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "true";
  let fetchCalls = 0;

  globalThis.fetch = async () => {
    fetchCalls += 1;
    return new Response(null, { status: 204 });
  };

  await assert.rejects(
    apiRequest({
      path: "/api/habits",
      method: "GET",
    }),
    (error: unknown) => error instanceof OfflineModeError,
  );

  assert.equal(fetchCalls, 0);
});

test("apiRequest rejects localhost for native apps", async () => {
  process.env.NEXT_PUBLIC_API_URL = "http://localhost:5000";
  Capacitor.isNativePlatform = () => true;
  let fetchCalls = 0;

  globalThis.fetch = async () => {
    fetchCalls += 1;
    return new Response(null, { status: 204 });
  };

  await assert.rejects(
    apiRequest({
      path: "/api/habits",
      method: "GET",
    }),
    (error: unknown) =>
      error instanceof AppError &&
      error.code === "config_error" &&
      error.message.includes("localhost"),
  );

  assert.equal(fetchCalls, 0);
});

test("apiRequest requires NEXT_PUBLIC_API_URL outside development-like web runtimes", async () => {
  mutableEnv.NODE_ENV = "production";
  let fetchCalls = 0;

  globalThis.fetch = async () => {
    fetchCalls += 1;
    return new Response(null, { status: 204 });
  };

  await assert.rejects(
    apiRequest({
      path: "/api/habits",
      method: "GET",
    }),
    (error: unknown) =>
      error instanceof AppError &&
      error.code === "config_error" &&
      error.message.includes("NEXT_PUBLIC_API_URL"),
  );

  assert.equal(fetchCalls, 0);
});

test("apiRequest accepts a LAN IP for native apps", async () => {
  process.env.NEXT_PUBLIC_API_URL = "http://192.168.1.50:5000/";
  Capacitor.isNativePlatform = () => true;

  globalThis.fetch = async (input) => {
    assert.equal(input, "http://192.168.1.50:5000/api/habits");

    return new Response(JSON.stringify([{ id: 2 }]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const result = await apiRequest<Array<{ id: number }>>({
    path: "/api/habits",
    method: "GET",
  });

  assert.deepEqual(result, [{ id: 2 }]);
});

test("apiRequest clears session and throws on 401 responses", async () => {
  window.sessionStorage.setItem("access_token", "expired-token");
  window.sessionStorage.setItem("refresh_token", "expired-refresh");
  window.localStorage.setItem("user", JSON.stringify({ id: 7, email: "test@example.com" }));

  globalThis.fetch = async () =>
    new Response(JSON.stringify({ error: "Token expired." }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });

  await assert.rejects(
    apiRequest({
      path: "/api/habits",
      method: "GET",
    }),
    (error: unknown) => {
      assert.ok(error instanceof AppError);
      assert.equal(error.code, "auth_required");
      assert.equal(error.message, "Token expired.");
      return true;
    },
  );

  assert.equal(window.sessionStorage.getItem("access_token"), null);
  assert.equal(window.sessionStorage.getItem("refresh_token"), null);
  assert.equal(window.localStorage.getItem("user"), null);
});

test("connected mode maps transport failures to app errors without enabling offline fallback", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(
    apiRequest({
      path: "/api/habits",
      method: "GET",
    }),
    (error: unknown) => {
      assert.ok(error instanceof AppError);
      assert.equal(error.code, "network_unavailable");
      assert.equal(
        error.message,
        "No se pudo conectar con el servidor. Verifica tu conexión e inténtalo de nuevo.",
      );
      assert.equal(isAppErrorCode(error, "network_unavailable"), true);
      return true;
    },
  );

  assert.equal(shouldUseOfflineFallback(new OfflineModeError()), true);
  assert.equal(shouldUseOfflineFallback(new AppError("network_unavailable", "network")), false);
});
