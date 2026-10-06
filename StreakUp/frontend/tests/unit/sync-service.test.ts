import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { saveSession } from "@/services/auth/authService";
import { DB_KEYS } from "@/services/storage/offlineDb";
import { drainSyncQueue, recoverInterruptedSync } from "@/services/sync/syncService";
import { getPendingOps, getSyncableOps } from "@/services/sync/syncQueue";
import { resetCredentialStore } from "@/services/auth/credentialProvider";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;
const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
}

function createValidAccessToken(): string {
  return buildJwt({ sub: "7", exp: Math.floor(Date.now() / 1000) + 3600 });
}

function createStorage(): Storage {
  const store = new Map<string, string>();
  return {
    clear() { store.clear(); },
    getItem(key) { return store.get(key) ?? null; },
    key(index) { return Array.from(store.keys())[index] ?? null; },
    get length() { return store.size; },
    removeItem(key) { store.delete(key); },
    setItem(key, value) { store.set(key, String(value)); },
  };
}

function createWindow() {
  return { localStorage: createStorage(), sessionStorage: createStorage(), location: { href: "" } };
}

function createDocument() {
  let cookie = "";
  return {
    get cookie() { return cookie; },
    set cookie(value: string) { cookie = value; },
  };
}

function seedSession() {
  saveSession({
    access_token: createValidAccessToken(),
    refresh_token: "refresh",
    user: {
      id: 7,
      username: "sync-user",
      email: "sync@example.com",
      role: "user",
      created_at: "2026-01-01T00:00:00Z",
    },
  });
}

function seedPendingOp(overrides: Record<string, unknown> = {}) {
  window.localStorage.setItem(
    DB_KEYS.pendingOps,
    JSON.stringify([
      {
        id: "op-1",
        kind: "toggle_checkin",
        userId: 7,
        payload: { habit_id: 11, date: "2026-05-04" },
        createdAt: "2026-05-04T00:00:00Z",
        status: "pending",
        attemptCount: 0,
        ...overrides,
      },
    ]),
  );
}

beforeEach(() => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "";
  process.env.NEXT_PUBLIC_API_URL = "";

  Object.defineProperty(globalThis, "window", { configurable: true, value: createWindow() });
  Object.defineProperty(globalThis, "document", { configurable: true, value: createDocument() });
  seedSession();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  resetCredentialStore();
  Object.defineProperty(globalThis, "window", { configurable: true, value: originalWindow });
  Object.defineProperty(globalThis, "document", { configurable: true, value: originalDocument });

  if (originalOfflineMode === undefined) {
    delete process.env.NEXT_PUBLIC_OFFLINE_MODE;
  } else {
    process.env.NEXT_PUBLIC_OFFLINE_MODE = originalOfflineMode;
  }

  if (originalApiBaseUrl === undefined) {
    delete process.env.NEXT_PUBLIC_API_URL;
  } else {
    process.env.NEXT_PUBLIC_API_URL = originalApiBaseUrl;
  }
});

test("drainSyncQueue posts pending operations and removes acknowledged ones", async () => {
  seedPendingOp();
  let fetchCalls = 0;

  globalThis.fetch = async (input, init) => {
    fetchCalls += 1;
    assert.equal(input, "/api/sync");
    assert.equal(init?.method, "POST");
    assert.equal(
      init?.body,
      JSON.stringify({
        operations: [
          {
            client_operation_id: "op-1",
            operation_type: "toggle_checkin",
            payload: { habit_id: 11, date: "2026-05-04" },
            created_at: "2026-05-04T00:00:00Z",
          },
        ],
      }),
    );

    return new Response(
      JSON.stringify({
        results: [
          {
            client_operation_id: "op-1",
            operation_type: "toggle_checkin",
            status: "acked",
            result: { checked: true, habit_id: 11, date: "2026-05-04" },
          },
        ],
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  };

  const result = await drainSyncQueue();

  assert.equal(fetchCalls, 1);
  assert.deepEqual(result, { attempted: 1, acked: 1, failed: 0, retryable: 0 });
  assert.equal(getPendingOps(7).length, 0);
  assert.deepEqual(JSON.parse(window.localStorage.getItem(DB_KEYS.checkins) ?? "[]"), [
    { user_id: 7, habit_id: 11, date: "2026-05-04" },
  ]);
});

test("drainSyncQueue keeps retryable failures pending", async () => {
  seedPendingOp();
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  const result = await drainSyncQueue();
  const ops = getSyncableOps(7);

  assert.deepEqual(result, { attempted: 1, acked: 0, failed: 0, retryable: 1 });
  assert.equal(ops.length, 1);
  assert.equal(ops[0]?.status, "pending");
  assert.equal(ops[0]?.attemptCount, 1);
});

test("drainSyncQueue marks permanent server failures failed", async () => {
  seedPendingOp();
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        results: [
          {
            client_operation_id: "op-1",
            operation_type: "toggle_checkin",
            status: "conflict",
            error: { code: "conflict", message: "requires validation", retryable: false },
          },
        ],
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );

  const result = await drainSyncQueue();
  const stored = JSON.parse(window.localStorage.getItem(DB_KEYS.pendingOps) ?? "[]");

  assert.deepEqual(result, { attempted: 1, acked: 0, failed: 1, retryable: 0 });
  assert.equal(getPendingOps(7).length, 0);
  assert.equal(stored[0]?.status, "failed_permanent");
  assert.equal(stored[0]?.lastError, "requires validation");
});

test("recoverInterruptedSync resets stale in-flight operations", () => {
  seedPendingOp({ status: "in_flight", attemptCount: 2 });

  recoverInterruptedSync();

  const ops = getSyncableOps(7);
  assert.equal(ops.length, 1);
  assert.equal(ops[0]?.status, "pending");
  assert.equal(ops[0]?.attemptCount, 2);
});
