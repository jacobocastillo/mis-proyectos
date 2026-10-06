import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { saveSession } from "@/services/auth/authService";
import { toggleCheckin, fetchTodayHabits } from "@/services/checkins/checkinService";
import { getLocalTodayHabits } from "@/services/storage/localData";
import { DB_KEYS } from "@/services/storage/offlineDb";
import { getPendingOps, hasPendingCheckin } from "@/services/sync/syncQueue";
import { resetCredentialStore } from "@/services/auth/credentialProvider";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;
const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

const SIMPLE_HABIT = {
  id: -1,
  user_id: 7,
  name: "Simple Habit",
  icon: "Flame",
  habit_type: "boolean" as const,
  frequency: "daily" as const,
  section: "fire" as const,
  target_duration: null,
  pomodoro_enabled: false,
  target_quantity: null,
  target_unit: null,
  // No validation_type — eligible for offline toggle
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const VALIDATION_HABIT = {
  ...SIMPLE_HABIT,
  id: -2,
  name: "Photo Habit",
  validation_type: "foto" as const,
};

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

beforeEach(() => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "true";
  process.env.NEXT_PUBLIC_API_URL = "";

  Object.defineProperty(globalThis, "window", { configurable: true, value: createWindow() });
  Object.defineProperty(globalThis, "document", { configurable: true, value: createDocument() });

  saveSession({
    access_token: createValidAccessToken(),
    refresh_token: "refresh",
    user: {
      id: 7,
      username: "alice",
      email: "alice@example.com",
      role: "user",
      created_at: "2026-01-01T00:00:00Z",
    },
  });
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

test("offline check-in writes pending operation and updates local read model", async () => {
  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([SIMPLE_HABIT]));

  const today = new Date().toISOString().slice(0, 10);
  const result = await toggleCheckin({ habit_id: -1 });

  assert.equal(result.checked, true);
  assert.equal(result.habit_id, -1);
  assert.equal(result.date, today);

  const ops = getPendingOps(7);
  assert.equal(ops.length, 1);
  assert.equal(ops[0]?.kind, "toggle_checkin");
  assert.deepEqual(ops[0]?.payload, { habit_id: -1, date: today });

  const todayHabits = getLocalTodayHabits(7);
  const habit = todayHabits.find((h) => h.id === -1);
  assert.ok(habit?.checked_today, "habit should be checked in local read model");
});

test("pending operation and checked state survive a simulated page reload", () => {
  const today = new Date().toISOString().slice(0, 10);

  // Simulate state written by a previous session
  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([SIMPLE_HABIT]));
  window.localStorage.setItem(DB_KEYS.checkins, JSON.stringify([{ user_id: 7, habit_id: -1, date: today }]));
  window.localStorage.setItem(
    DB_KEYS.pendingOps,
    JSON.stringify([
      {
        id: "test-reload-1",
        kind: "toggle_checkin",
        userId: 7,
        payload: { habit_id: -1, date: today },
        createdAt: new Date().toISOString(),
      },
    ]),
  );

  // After reload, reads come from localStorage directly
  const ops = getPendingOps(7);
  assert.equal(ops.length, 1);
  assert.equal(ops[0]?.kind, "toggle_checkin");

  const todayHabits = getLocalTodayHabits(7);
  const habit = todayHabits.find((h) => h.id === -1);
  assert.ok(habit?.checked_today, "checked state should survive reload");
});

test("duplicate offline toggles are deterministic — second toggle cancels the first", async () => {
  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([SIMPLE_HABIT]));

  // Toggle ON
  const r1 = await toggleCheckin({ habit_id: -1 });
  assert.equal(r1.checked, true);
  assert.equal(getPendingOps(7).length, 1);

  // Toggle OFF — should cancel the pending op
  const r2 = await toggleCheckin({ habit_id: -1 });
  assert.equal(r2.checked, false);
  assert.equal(getPendingOps(7).length, 0);

  // Toggle ON again — re-enqueue
  const r3 = await toggleCheckin({ habit_id: -1 });
  assert.equal(r3.checked, true);
  assert.equal(getPendingOps(7).length, 1);
});

test("validation-driven habit offline attempt shows clear unsupported message", async () => {
  window.localStorage.setItem(DB_KEYS.habits, JSON.stringify([VALIDATION_HABIT]));

  await assert.rejects(
    toggleCheckin({ habit_id: -2 }),
    /requiere validación del servidor/,
  );

  // No checkin or pending op written
  assert.equal(window.localStorage.getItem(DB_KEYS.checkins), null);
  assert.equal(getPendingOps(7).length, 0);
});
