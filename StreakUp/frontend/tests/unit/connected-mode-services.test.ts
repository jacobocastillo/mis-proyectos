import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { saveSession } from "@/services/auth/authService";
import { fetchTodayHabits, toggleCheckin } from "@/services/checkins/checkinService";
import { createHabit, fetchHabits } from "@/services/habits/habitService";
import { createPomodoroSession } from "@/services/pomodoro/pomodoroService";
import { applyReminderSchedule } from "@/services/reminders/reminderService";
import { fetchStatsSummary } from "@/services/stats/statsService";
import { resetCredentialStore } from "@/services/auth/credentialProvider";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;
const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

const LOCAL_HABITS_KEY = "streakup.local.habits";
const LOCAL_CHECKINS_KEY = "streakup.local.checkins";
const LOCAL_POMODORO_KEY = "streakup.local.pomodoroSessions";
const REMINDER_KEY = "streakup.reminders.preferences.7";

function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
}

function createValidAccessToken(): string {
  return buildJwt({
    sub: "7",
    exp: Math.floor(Date.now() / 1000) + 3600,
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

function seedSavedSession() {
  saveSession({
    access_token: createValidAccessToken(),
    refresh_token: "saved-refresh",
    user: {
      id: 7,
      username: "alice",
      email: "alice@example.com",
      role: "user",
      created_at: "2026-04-05T00:00:00Z",
    },
  });
}

beforeEach(() => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "";
  process.env.NEXT_PUBLIC_API_URL = "";

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: createWindow(),
  });

  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: createDocument(),
  });

  seedSavedSession();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  resetCredentialStore();

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

  if (originalApiBaseUrl === undefined) {
    delete process.env.NEXT_PUBLIC_API_URL;
  } else {
    process.env.NEXT_PUBLIC_API_URL = originalApiBaseUrl;
  }
});

test("connected mode write failures do not fabricate local success", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(createHabit({ habito_id: 1 }), /No se pudo conectar con el servidor/);
  await assert.rejects(toggleCheckin({ habit_id: 1 }), /No se pudo conectar con el servidor/);
  await assert.rejects(createPomodoroSession({ theme: "fire" }), /No se pudo conectar con el servidor/);

  assert.equal(window.localStorage.getItem(LOCAL_HABITS_KEY), null);
  assert.equal(window.localStorage.getItem(LOCAL_CHECKINS_KEY), null);
  assert.equal(window.localStorage.getItem(LOCAL_POMODORO_KEY), null);
});

test("connected mode read failures reject instead of replaying cached local data", async () => {
  window.localStorage.setItem(
    LOCAL_HABITS_KEY,
    JSON.stringify([
      {
        id: -1,
        user_id: 7,
        name: "Hábito Offline",
        icon: "Flame",
        habit_type: "boolean",
        frequency: "daily",
        section: "fire",
        target_duration: null,
        pomodoro_enabled: false,
        target_quantity: null,
        target_unit: null,
        created_at: "2026-04-05T00:00:00Z",
        updated_at: "2026-04-05T00:00:00Z",
      },
    ]),
  );

  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(fetchHabits(), /No se pudo conectar con el servidor/);
  await assert.rejects(fetchTodayHabits(), /No se pudo conectar con el servidor/);
  await assert.rejects(fetchStatsSummary(), /No se pudo conectar con el servidor/);
});

test("offline mode still uses local emulation only when explicitly enabled", async () => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "true";
  let fetchCalls = 0;

  globalThis.fetch = async () => {
    fetchCalls += 1;
    return new Response(null, { status: 204 });
  };

  const createdHabit = await createHabit({ habito_id: 1 });
  const offlineHabits = await fetchHabits();

  assert.equal(fetchCalls, 0);
  assert.ok(createdHabit.id < 0);
  // Habit created offline defaults to validation_type "foto" — must reject with validation-gated message
  await assert.rejects(
    toggleCheckin({ habit_id: createdHabit.id }),
    /requiere validación del servidor/,
  );
  assert.equal(offlineHabits.length, 1);
  assert.equal(offlineHabits[0]?.id, createdHabit.id);
  assert.equal(window.localStorage.getItem(LOCAL_CHECKINS_KEY), null);
});

test("offline mode read cache respects weekly and custom schedules", async () => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "true";
  const today = new Date().toISOString().slice(0, 10);
  const mondayFirstToday = (new Date(`${today}T00:00:00`).getDay() + 6) % 7;

  window.localStorage.setItem(
    LOCAL_HABITS_KEY,
    JSON.stringify([
      {
        id: -1,
        user_id: 7,
        name: "Weekly",
        icon: "Flame",
        habit_type: "boolean",
        frequency: "weekly",
        section: "fire",
        target_duration: null,
        pomodoro_enabled: false,
        target_quantity: null,
        target_unit: null,
        created_at: "2026-04-05T00:00:00Z",
        updated_at: "2026-04-05T00:00:00Z",
      },
      {
        id: -2,
        user_id: 7,
        name: "Custom Today",
        icon: "Flame",
        habit_type: "boolean",
        frequency: "custom",
        schedule_days: [mondayFirstToday],
        section: "fire",
        target_duration: null,
        pomodoro_enabled: false,
        target_quantity: null,
        target_unit: null,
        created_at: "2026-04-05T00:00:00Z",
        updated_at: "2026-04-05T00:00:00Z",
      },
      {
        id: -3,
        user_id: 7,
        name: "Custom Empty",
        icon: "Flame",
        habit_type: "boolean",
        frequency: "custom",
        schedule_days: [],
        section: "fire",
        target_duration: null,
        pomodoro_enabled: false,
        target_quantity: null,
        target_unit: null,
        created_at: "2026-04-05T00:00:00Z",
        updated_at: "2026-04-05T00:00:00Z",
      },
    ]),
  );

  const habits = await fetchTodayHabits();
  assert.deepEqual(
    habits.map((habit) => habit.name),
    ["Custom Today", "Weekly"],
  );
});

test("offline mode stats never invent XP from cached check-ins", async () => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "true";
  const today = new Date().toISOString().slice(0, 10);

  window.localStorage.setItem(
    LOCAL_HABITS_KEY,
    JSON.stringify([
      {
        id: -1,
        user_id: 7,
        name: "Cached Habit",
        icon: "Flame",
        habit_type: "boolean",
        frequency: "daily",
        section: "fire",
        target_duration: null,
        pomodoro_enabled: false,
        target_quantity: null,
        target_unit: null,
        created_at: "2026-04-05T00:00:00Z",
        updated_at: "2026-04-05T00:00:00Z",
      },
    ]),
  );
  window.localStorage.setItem(
    LOCAL_CHECKINS_KEY,
    JSON.stringify([{ user_id: 7, habit_id: -1, date: today }]),
  );

  const stats = await fetchStatsSummary();

  assert.equal(stats.today_completed, 1);
  assert.equal(stats.today_total, 1);
  assert.equal(stats.total_xp, 0);
  assert.equal(stats.level, 1);
  assert.equal(stats.validations_today, 0);
});

test("reminder scheduling stays local and does not create progress records", async () => {
  const notifications = {
    async checkPermissions() {
      return { display: "granted" as const };
    },
    async requestPermissions() {
      return { display: "granted" as const };
    },
    async getPending() {
      return { notifications: [] };
    },
    async cancel() {},
    async schedule() {
      return { notifications: [{ id: 39000 }] };
    },
  };

  const result = await applyReminderSchedule(
    { enabled: true, time: "09:00", days: [0] },
    [
      {
        active: true,
        frequency: "daily",
        schedule_days: [],
      },
    ],
    {
      canUseStorage: () => true,
      getCurrentUserId: () => 7,
      isNativePlatform: () => true,
      notifications,
    },
  );

  assert.equal(result.status, "scheduled");
  assert.equal(result.scheduledCount, 1);
  assert.ok(window.localStorage.getItem(REMINDER_KEY));
  assert.equal(window.localStorage.getItem(LOCAL_CHECKINS_KEY), null);
  assert.equal(window.localStorage.getItem(LOCAL_POMODORO_KEY), null);
});

test("fetchTodayHabits propagates checked_today=true from backend response", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify([
        {
          id: 10,
          user_id: 7,
          name: "Ejercicio",
          icon: "Flame",
          habit_type: "boolean",
          frequency: "daily",
          section: "fire",
          validation_type: "foto",
          target_duration: null,
          pomodoro_enabled: false,
          target_quantity: null,
          target_unit: null,
          created_at: "2026-04-05T00:00:00Z",
          updated_at: "2026-04-05T00:00:00Z",
          checked_today: true,
        },
      ]),
      { status: 200, headers: { "content-type": "application/json" } },
    );

  const habits = await fetchTodayHabits();
  assert.equal(habits.length, 1);
  assert.equal(habits[0]?.checked_today, true);
});

test("fetchTodayHabits propagates checked_today=false from backend response", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify([
        {
          id: 11,
          user_id: 7,
          name: "Meditación",
          icon: "Moon",
          habit_type: "boolean",
          frequency: "daily",
          section: "moon",
          validation_type: "texto",
          target_duration: null,
          pomodoro_enabled: false,
          target_quantity: null,
          target_unit: null,
          created_at: "2026-04-05T00:00:00Z",
          updated_at: "2026-04-05T00:00:00Z",
          checked_today: false,
        },
      ]),
      { status: 200, headers: { "content-type": "application/json" } },
    );

  const habits = await fetchTodayHabits();
  assert.equal(habits.length, 1);
  assert.equal(habits[0]?.checked_today, false);
});
