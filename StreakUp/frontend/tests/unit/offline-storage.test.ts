import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import {
  DB_KEYS,
  SCHEMA_VERSION,
  SCHEMA_VERSION_KEY,
  OfflineStorageError,
  clearOfflineData,
  dbRead,
  dbWrite,
  getSchemaVersion,
} from "@/services/storage/offlineDb";
import { runMigrationsOnce } from "@/services/storage/localMigrations";
import { getLocalHabits, cacheHabits } from "@/services/storage/localData";

const originalWindow = globalThis.window;
const originalDocument = globalThis.document;

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
    location: { href: "" },
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
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });

  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: originalDocument,
  });
});

test("local schema initializes empty on fresh storage", () => {
  assert.equal(getSchemaVersion(), 0);

  runMigrationsOnce();

  assert.equal(getSchemaVersion(), SCHEMA_VERSION);
  // Absent keys stay absent — migration does not pre-populate unused stores
  assert.equal(window.localStorage.getItem(DB_KEYS.habits), null);
  assert.equal(window.localStorage.getItem(DB_KEYS.checkins), null);
  assert.equal(window.localStorage.getItem(DB_KEYS.pomodoroSessions), null);
  // pendingOps always initialized so queued ops survive page reload
  assert.deepEqual(dbRead(DB_KEYS.pendingOps, null), []);
});

test("existing localStorage cache migrates once and is preserved", () => {
  const existingHabit = {
    id: -1,
    user_id: 7,
    name: "Old Cached Habit",
    icon: "Flame",
    habit_type: "boolean",
    frequency: "daily",
    section: "fire",
    target_duration: null,
    pomodoro_enabled: false,
    target_quantity: null,
    target_unit: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const existingCheckin = { user_id: 7, habit_id: -1, date: "2026-01-01" };

  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([existingHabit]));
  window.localStorage.setItem(DB_KEYS.checkins, JSON.stringify([existingCheckin]));

  assert.equal(getSchemaVersion(), 0);

  runMigrationsOnce();

  assert.equal(getSchemaVersion(), SCHEMA_VERSION);
  assert.deepEqual(dbRead(DB_KEYS.habits, []), [existingHabit]);
  assert.deepEqual(dbRead(DB_KEYS.checkins, []), [existingCheckin]);
  // pomodoroSessions was absent before migration — stays absent
  assert.equal(window.localStorage.getItem(DB_KEYS.pomodoroSessions), null);
  // pendingOps always initialized
  assert.deepEqual(dbRead(DB_KEYS.pendingOps, null), []);
});

test("migration does not re-run once schema version is set", () => {
  const habit = { id: -1, user_id: 7, name: "Habit" };
  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([habit]));

  runMigrationsOnce();
  assert.equal(getSchemaVersion(), SCHEMA_VERSION);

  // Mutate storage after migration
  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([]));

  // Second call should skip migration — habits already cleared in storage
  runMigrationsOnce();

  assert.deepEqual(dbRead(DB_KEYS.habits, null), []);
});

test("corrupt local records are quarantined and return fallback", () => {
  window.localStorage.setItem(DB_KEYS.habits, "{bad json[[[");

  const result = dbRead<unknown[]>(DB_KEYS.habits, []);

  assert.deepEqual(result, []);
  assert.equal(window.localStorage.getItem(DB_KEYS.habits), null);
});

test("dbWrite throws OfflineStorageError on quota exceeded", () => {
  const quotaError = new DOMException("quota", "QuotaExceededError");
  const originalSetItem = window.localStorage.setItem.bind(window.localStorage);
  window.localStorage.setItem = (_key: string, _value: string) => {
    throw quotaError;
  };

  assert.throws(
    () => dbWrite(DB_KEYS.habits, []),
    (err: unknown) => err instanceof OfflineStorageError && err.kind === "quota",
  );

  window.localStorage.setItem = originalSetItem;
});

test("cached reads remain user-scoped", () => {
  const habitUser7 = {
    id: 1,
    user_id: 7,
    name: "User 7 Habit",
    icon: "Flame",
    habit_type: "boolean" as const,
    frequency: "daily" as const,
    section: "fire" as const,
    target_duration: null,
    pomodoro_enabled: false,
    target_quantity: null,
    target_unit: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const habitUser8 = { ...habitUser7, id: 2, user_id: 8, name: "User 8 Habit" };

  window.localStorage.setItem(
    DB_KEYS.habits,
    JSON.stringify([habitUser7, habitUser8]),
  );

  const habits7 = getLocalHabits(7);
  const habits8 = getLocalHabits(8);

  assert.equal(habits7.length, 1);
  assert.equal(habits7[0]?.user_id, 7);
  assert.equal(habits8.length, 1);
  assert.equal(habits8[0]?.user_id, 8);
});

test("clearOfflineData removes local caches and schema version", () => {
  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([{ id: 1 }]));
  window.localStorage.setItem(DB_KEYS.checkins, JSON.stringify([{ habit_id: 1 }]));
  window.localStorage.setItem(DB_KEYS.pendingOps, JSON.stringify([{ id: "op-1" }]));
  window.localStorage.setItem(SCHEMA_VERSION_KEY, String(SCHEMA_VERSION));
  window.localStorage.setItem("user", JSON.stringify({ id: 7 }));

  clearOfflineData();

  assert.equal(window.localStorage.getItem(DB_KEYS.habits), null);
  assert.equal(window.localStorage.getItem(DB_KEYS.checkins), null);
  assert.equal(window.localStorage.getItem(DB_KEYS.pendingOps), null);
  assert.equal(window.localStorage.getItem(SCHEMA_VERSION_KEY), null);
  assert.notEqual(window.localStorage.getItem("user"), null);
});
