import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { clearAccountLocalData } from "@/services/auth/accountService";
import { DB_KEYS, SCHEMA_VERSION_KEY } from "@/services/storage/offlineDb";
import { installBrowserTestEnv, restoreBrowserTestEnv } from "../test-utils";

// Requirement mapping:
// RNF-12: Account deletion cleanup removes local offline data without clearing unrelated profile cache.

beforeEach(installBrowserTestEnv);
afterEach(restoreBrowserTestEnv);

test("RNF-12 local account cleanup removes offline caches and pending operations", () => {
  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([{ id: 1 }]));
  window.localStorage.setItem(DB_KEYS.checkins, JSON.stringify([{ habit_id: 1 }]));
  window.localStorage.setItem(DB_KEYS.pomodoroSessions, JSON.stringify([{ id: 1 }]));
  window.localStorage.setItem(DB_KEYS.pendingOps, JSON.stringify([{ id: "op-1" }]));
  window.localStorage.setItem(SCHEMA_VERSION_KEY, "1");
  window.localStorage.setItem("user", JSON.stringify({ id: 7 }));

  clearAccountLocalData();

  assert.equal(window.localStorage.getItem(DB_KEYS.habits), null);
  assert.equal(window.localStorage.getItem(DB_KEYS.checkins), null);
  assert.equal(window.localStorage.getItem(DB_KEYS.pomodoroSessions), null);
  assert.equal(window.localStorage.getItem(DB_KEYS.pendingOps), null);
  assert.equal(window.localStorage.getItem(SCHEMA_VERSION_KEY), null);
  assert.notEqual(window.localStorage.getItem("user"), null);
});
