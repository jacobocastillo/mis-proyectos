import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { saveSession } from "@/services/auth/authService";
import { DB_KEYS } from "@/services/storage/offlineDb";
import { drainSyncQueue } from "@/services/sync/syncService";
import { getPendingOps } from "@/services/sync/syncQueue";
import { buildJwt, installBrowserTestEnv, restoreBrowserTestEnv } from "../test-utils";

// Requirement mapping:
// RNF-04: Pending offline operations sync automatically and are removed once acknowledged.

beforeEach(() => {
  installBrowserTestEnv();
  saveSession({
    access_token: buildJwt({ sub: "7", exp: Math.floor(Date.now() / 1000) + 3600 }),
    refresh_token: "refresh",
    user: {
      id: 7,
      username: "sync-user",
      email: "sync@example.com",
      role: "user",
      created_at: "2026-01-01T00:00:00Z",
    },
  });
  window.localStorage.setItem(
    DB_KEYS.pendingOps,
    JSON.stringify([
      {
        id: "op-rnf-04",
        kind: "toggle_checkin",
        userId: 7,
        payload: { habit_id: 11, date: "2026-05-04" },
        createdAt: "2026-05-04T00:00:00Z",
        status: "pending",
        attemptCount: 0,
      },
    ]),
  );
});

afterEach(restoreBrowserTestEnv);

test("RNF-04 acknowledged sync operation is removed from the local queue", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        results: [
          {
            client_operation_id: "op-rnf-04",
            operation_type: "toggle_checkin",
            status: "acked",
            result: { checked: true, habit_id: 11, date: "2026-05-04" },
          },
        ],
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );

  const result = await drainSyncQueue();

  assert.deepEqual(result, { attempted: 1, acked: 1, failed: 0, retryable: 0 });
  assert.equal(getPendingOps(7).length, 0);
});
