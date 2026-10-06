import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { Weekday } from "@capacitor/local-notifications";
import {
  applyReminderSchedule,
  getEffectiveReminderDays,
  loadReminderPreferences,
  saveReminderPreferences,
} from "@/services/reminders/reminderService";
import type { Habit } from "@/types/habits";

const originalWindow = globalThis.window;

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
  };
}

function createHabit(overrides: Partial<Habit>): Habit {
  return {
    id: 1,
    user_id: 7,
    name: "Test habit",
    icon: "Flame",
    habit_type: "boolean",
    frequency: "daily",
    section: "fire",
    target_duration: null,
    pomodoro_enabled: false,
    target_quantity: null,
    target_unit: null,
    schedule_days: [],
    created_at: "2026-05-03T00:00:00Z",
    updated_at: "2026-05-03T00:00:00Z",
    ...overrides,
  };
}

function createNotificationsAdapter(options: {
  check?: "prompt" | "prompt-with-rationale" | "granted" | "denied";
  request?: "prompt" | "prompt-with-rationale" | "granted" | "denied";
  pendingIds?: number[];
} = {}) {
  const calls = {
    cancelled: [] as number[],
    scheduled: [] as Array<{ id: number; weekday?: Weekday; hour?: number; minute?: number }>,
    requested: 0,
  };

  const adapter = {
    async checkPermissions() {
      return { display: options.check ?? "granted" };
    },
    async requestPermissions() {
      calls.requested += 1;
      return { display: options.request ?? "granted" };
    },
    async getPending() {
      return {
        notifications: (options.pendingIds ?? []).map((id) => ({ id })),
      };
    },
    async cancel(payload: { notifications: Array<{ id: number }> }) {
      calls.cancelled.push(...payload.notifications.map((notification) => notification.id));
    },
    async schedule(payload: {
      notifications: Array<{
        id: number;
        schedule?: { on?: { weekday?: Weekday; hour?: number; minute?: number } };
      }>;
    }) {
      calls.scheduled.push(
        ...payload.notifications.map((notification) => ({
          id: notification.id,
          weekday: notification.schedule?.on?.weekday,
          hour: notification.schedule?.on?.hour,
          minute: notification.schedule?.on?.minute,
        })),
      );
      return { notifications: payload.notifications.map((notification) => ({ id: notification.id })) };
    },
  };

  return { adapter, calls };
}

beforeEach(() => {
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: createWindow(),
  });
});

afterEach(() => {
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
});

test("reminder preferences are stored per user", () => {
  const env = {
    canUseStorage: () => true,
    getCurrentUserId: () => 7,
  };

  saveReminderPreferences({ enabled: true, time: "19:30", days: [1, 3] }, env);

  assert.deepEqual(loadReminderPreferences(env), {
    enabled: true,
    time: "19:30",
    days: [1, 3],
  });
  assert.deepEqual(
    loadReminderPreferences({ ...env, getCurrentUserId: () => 8 }),
    { enabled: false, time: "08:00", days: [0, 1, 2, 3, 4, 5, 6] },
  );
});

test("effective reminder days respect custom habit schedules", () => {
  const days = getEffectiveReminderDays(
    { days: [0, 1, 2, 3, 4] },
    [
      createHabit({ frequency: "custom", schedule_days: [1, 3] }),
      createHabit({ active: false, frequency: "daily" }),
    ],
  );

  assert.deepEqual(days, [1, 3]);
});

test("weekly habits are eligible on selected reminder days", () => {
  const days = getEffectiveReminderDays(
    { days: [1, 2, 3] },
    [createHabit({ frequency: "weekly" })],
  );

  assert.deepEqual(days, [1, 2, 3]);
});

test("disabled reminders cancel existing reminder notifications", async () => {
  const { adapter, calls } = createNotificationsAdapter({
    pendingIds: [39000, 39002, 12],
  });

  const result = await applyReminderSchedule(
    { enabled: false, time: "08:00", days: [0, 1, 2] },
    [createHabit({})],
    {
      canUseStorage: () => true,
      getCurrentUserId: () => 7,
      isNativePlatform: () => true,
      notifications: adapter,
    },
  );

  assert.equal(result.status, "disabled");
  assert.deepEqual(calls.cancelled, [39000, 39002]);
  assert.deepEqual(calls.scheduled, []);
});

test("permission denial prevents scheduling", async () => {
  const { adapter, calls } = createNotificationsAdapter({
    check: "prompt",
    request: "denied",
    pendingIds: [39000],
  });

  const result = await applyReminderSchedule(
    { enabled: true, time: "08:00", days: [0] },
    [createHabit({})],
    {
      canUseStorage: () => true,
      getCurrentUserId: () => 7,
      isNativePlatform: () => true,
      notifications: adapter,
    },
  );

  assert.equal(result.status, "permission_denied");
  assert.equal(result.permission, "denied");
  assert.equal(calls.requested, 1);
  assert.deepEqual(calls.cancelled, [39000]);
  assert.deepEqual(calls.scheduled, []);
});

test("native scheduling maps Monday-first days to Capacitor weekdays", async () => {
  const { adapter, calls } = createNotificationsAdapter();

  const result = await applyReminderSchedule(
    { enabled: true, time: "18:45", days: [1, 3] },
    [createHabit({ frequency: "custom", schedule_days: [1, 3] })],
    {
      canUseStorage: () => true,
      getCurrentUserId: () => 7,
      isNativePlatform: () => true,
      notifications: adapter,
    },
  );

  assert.equal(result.status, "scheduled");
  assert.equal(result.scheduledCount, 2);
  assert.deepEqual(calls.scheduled, [
    { id: 39001, weekday: Weekday.Tuesday, hour: 18, minute: 45 },
    { id: 39003, weekday: Weekday.Thursday, hour: 18, minute: 45 },
  ]);
});

test("web environment saves preferences but does not schedule notifications", async () => {
  const { adapter, calls } = createNotificationsAdapter();

  const result = await applyReminderSchedule(
    { enabled: true, time: "08:00", days: [0] },
    [createHabit({})],
    {
      canUseStorage: () => true,
      getCurrentUserId: () => 7,
      isNativePlatform: () => false,
      notifications: adapter,
    },
  );

  assert.equal(result.status, "unavailable");
  assert.deepEqual(calls.cancelled, []);
  assert.deepEqual(calls.scheduled, []);
  assert.equal(loadReminderPreferences({ canUseStorage: () => true, getCurrentUserId: () => 7 }).enabled, true);
});
