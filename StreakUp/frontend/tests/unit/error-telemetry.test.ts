import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { reportClientError } from "@/services/telemetry/errorTelemetry";
import { resetCredentialStore } from "@/services/auth/credentialProvider";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalNavigator = globalThis.navigator;
const originalNodeEnv = process.env.NODE_ENV;

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

beforeEach(() => {
  process.env.NODE_ENV = "test";
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      localStorage: createStorage(),
      sessionStorage: createStorage(),
      location: { href: "http://localhost:3000/profile" },
    },
  });
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { userAgent: "node-test-agent" },
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  resetCredentialStore();
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: originalNavigator,
  });

  if (originalNodeEnv === undefined) {
    delete process.env.NODE_ENV;
  } else {
    process.env.NODE_ENV = originalNodeEnv;
  }
});

test("reportClientError posts sanitized client error context", async () => {
  let body: Record<string, unknown> | null = null;

  globalThis.fetch = async (input, init) => {
    assert.equal(input, "/api/telemetry/errors");
    assert.equal(init?.method, "POST");
    body = JSON.parse(String(init?.body));

    return new Response(JSON.stringify({ status: "accepted" }), {
      status: 202,
      headers: { "Content-Type": "application/json" },
    });
  };

  await reportClientError(new Error("Boom"), "test-component");

  assert.equal(body?.message, "Boom");
  assert.equal(body?.name, "Error");
  assert.equal(body?.component, "test-component");
  assert.equal(body?.url, "http://localhost:3000/profile");
  assert.equal(body?.userAgent, "node-test-agent");
});

test("reportClientError swallows telemetry transport failures", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("network down");
  };

  await reportClientError(new Error("Boom"), "test-component");
});
