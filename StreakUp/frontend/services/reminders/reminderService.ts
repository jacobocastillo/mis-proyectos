import { Capacitor } from "@capacitor/core";
import { LocalNotifications, Weekday } from "@capacitor/local-notifications";
import type {
  LocalNotificationSchema,
  PermissionStatus,
} from "@capacitor/local-notifications";
import { getSession } from "@/services/auth/authService";
import type { Habit } from "@/types/habits";

export type ReminderPermissionState = PermissionStatus["display"] | "unavailable";
export type ReminderScheduleStatus =
  | "disabled"
  | "scheduled"
  | "permission_denied"
  | "unavailable"
  | "no_matching_habits";

export interface ReminderPreferences {
  enabled: boolean;
  time: string;
  days: number[];
}

export interface ReminderScheduleResult {
  status: ReminderScheduleStatus;
  scheduledCount: number;
  permission: ReminderPermissionState;
}

interface LocalNotificationsAdapter {
  checkPermissions: typeof LocalNotifications.checkPermissions;
  requestPermissions: typeof LocalNotifications.requestPermissions;
  getPending: typeof LocalNotifications.getPending;
  cancel: typeof LocalNotifications.cancel;
  schedule: typeof LocalNotifications.schedule;
}

interface ReminderServiceEnvironment {
  canUseStorage?: () => boolean;
  isNativePlatform?: () => boolean;
  notifications?: LocalNotificationsAdapter;
  getCurrentUserId?: () => number;
}

const STORAGE_KEY_PREFIX = "streakup.reminders.preferences";
const NOTIFICATION_ID_BASE = 39000;
const DEFAULT_PREFERENCES: ReminderPreferences = {
  enabled: false,
  time: "08:00",
  days: [0, 1, 2, 3, 4, 5, 6],
};

const MONDAY_FIRST_TO_CAPACITOR_WEEKDAY: Record<number, Weekday> = {
  0: Weekday.Monday,
  1: Weekday.Tuesday,
  2: Weekday.Wednesday,
  3: Weekday.Thursday,
  4: Weekday.Friday,
  5: Weekday.Saturday,
  6: Weekday.Sunday,
};

function defaultCanUseStorage(): boolean {
  return typeof window !== "undefined";
}

function defaultIsNativePlatform(): boolean {
  return Capacitor.isNativePlatform();
}

function defaultGetCurrentUserId(): number {
  const userId = Number(getSession()?.user.id ?? 0);
  return Number.isFinite(userId) ? userId : 0;
}

function getEnvironment(env: ReminderServiceEnvironment = {}): Required<ReminderServiceEnvironment> {
  return {
    canUseStorage: env.canUseStorage ?? defaultCanUseStorage,
    isNativePlatform: env.isNativePlatform ?? defaultIsNativePlatform,
    notifications: env.notifications ?? LocalNotifications,
    getCurrentUserId: env.getCurrentUserId ?? defaultGetCurrentUserId,
  };
}

function getStorageKey(userId: number): string {
  return `${STORAGE_KEY_PREFIX}.${userId > 0 ? userId : "anonymous"}`;
}

function normalizeTime(value: unknown): string {
  if (typeof value !== "string" || !/^\d{2}:\d{2}$/.test(value)) {
    return DEFAULT_PREFERENCES.time;
  }

  const [hours, minutes] = value.split(":").map(Number);
  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
    return DEFAULT_PREFERENCES.time;
  }

  return value;
}

export function normalizeReminderDays(days: unknown): number[] {
  if (!Array.isArray(days)) {
    return DEFAULT_PREFERENCES.days;
  }

  const normalized = Array.from(
    new Set(
      days
        .map((day) => Number(day))
        .filter((day) => Number.isInteger(day) && day >= 0 && day <= 6),
    ),
  ).sort((left, right) => left - right);

  return normalized.length > 0 ? normalized : DEFAULT_PREFERENCES.days;
}

export function normalizeReminderPreferences(value: unknown): ReminderPreferences {
  if (!value || typeof value !== "object") {
    return { ...DEFAULT_PREFERENCES };
  }

  const candidate = value as Partial<ReminderPreferences>;
  return {
    enabled: candidate.enabled === true,
    time: normalizeTime(candidate.time),
    days: normalizeReminderDays(candidate.days),
  };
}

export function loadReminderPreferences(
  env: ReminderServiceEnvironment = {},
): ReminderPreferences {
  const resolvedEnv = getEnvironment(env);
  if (!resolvedEnv.canUseStorage()) {
    return { ...DEFAULT_PREFERENCES };
  }

  const rawValue = window.localStorage.getItem(getStorageKey(resolvedEnv.getCurrentUserId()));
  if (!rawValue) {
    return { ...DEFAULT_PREFERENCES };
  }

  try {
    return normalizeReminderPreferences(JSON.parse(rawValue));
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

export function saveReminderPreferences(
  preferences: ReminderPreferences,
  env: ReminderServiceEnvironment = {},
): ReminderPreferences {
  const normalized = normalizeReminderPreferences(preferences);
  const resolvedEnv = getEnvironment(env);

  if (resolvedEnv.canUseStorage()) {
    window.localStorage.setItem(
      getStorageKey(resolvedEnv.getCurrentUserId()),
      JSON.stringify(normalized),
    );
  }

  return normalized;
}

export function areNativeRemindersAvailable(env: ReminderServiceEnvironment = {}): boolean {
  return getEnvironment(env).isNativePlatform();
}

export async function getReminderPermissionStatus(
  env: ReminderServiceEnvironment = {},
): Promise<ReminderPermissionState> {
  const resolvedEnv = getEnvironment(env);
  if (!resolvedEnv.isNativePlatform()) {
    return "unavailable";
  }

  const permission = await resolvedEnv.notifications.checkPermissions();
  return permission.display;
}

export async function requestReminderPermission(
  env: ReminderServiceEnvironment = {},
): Promise<ReminderPermissionState> {
  const resolvedEnv = getEnvironment(env);
  if (!resolvedEnv.isNativePlatform()) {
    return "unavailable";
  }

  const current = await resolvedEnv.notifications.checkPermissions();
  if (current.display === "granted") {
    return "granted";
  }

  const requested = await resolvedEnv.notifications.requestPermissions();
  return requested.display;
}

function getReminderNotificationId(day: number): number {
  return NOTIFICATION_ID_BASE + day;
}

function isReminderNotificationId(id: number): boolean {
  return id >= NOTIFICATION_ID_BASE && id <= NOTIFICATION_ID_BASE + 6;
}

export async function cancelScheduledReminders(
  env: ReminderServiceEnvironment = {},
): Promise<void> {
  const resolvedEnv = getEnvironment(env);
  if (!resolvedEnv.isNativePlatform()) {
    return;
  }

  const pending = await resolvedEnv.notifications.getPending();
  const notifications = pending.notifications
    .filter((notification) => isReminderNotificationId(notification.id))
    .map((notification) => ({ id: notification.id }));

  if (notifications.length > 0) {
    await resolvedEnv.notifications.cancel({ notifications });
  }
}

export function getEffectiveReminderDays(
  preferences: Pick<ReminderPreferences, "days">,
  habits: Pick<Habit, "active" | "frequency" | "schedule_days">[],
): number[] {
  const selectedDays = normalizeReminderDays(preferences.days);
  const activeHabits = habits.filter((habit) => habit.active !== false);

  return selectedDays.filter((day) =>
    activeHabits.some((habit) => {
      if (habit.frequency === "daily" || habit.frequency === "weekly") {
        return true;
      }

      if (habit.frequency === "custom") {
        return (habit.schedule_days ?? []).includes(day);
      }

      return false;
    }),
  );
}

function buildReminderNotifications(
  preferences: ReminderPreferences,
  habits: Pick<Habit, "active" | "frequency" | "schedule_days">[],
): LocalNotificationSchema[] {
  const [hour, minute] = preferences.time.split(":").map(Number);

  return getEffectiveReminderDays(preferences, habits).map((day) => ({
    id: getReminderNotificationId(day),
    title: "StreakUP",
    body: "Revisa tus hábitos de hoy y mantén tu racha.",
    schedule: {
      on: {
        weekday: MONDAY_FIRST_TO_CAPACITOR_WEEKDAY[day],
        hour,
        minute,
        second: 0,
      },
      allowWhileIdle: true,
    },
    autoCancel: true,
    extra: {
      source: "streakup-reminder",
      weekday: day,
    },
  }));
}

export async function applyReminderSchedule(
  preferences: ReminderPreferences,
  habits: Pick<Habit, "active" | "frequency" | "schedule_days">[],
  env: ReminderServiceEnvironment = {},
): Promise<ReminderScheduleResult> {
  const normalized = saveReminderPreferences(preferences, env);
  const resolvedEnv = getEnvironment(env);

  if (!resolvedEnv.isNativePlatform()) {
    return {
      status: "unavailable",
      scheduledCount: 0,
      permission: "unavailable",
    };
  }

  await cancelScheduledReminders(env);

  if (!normalized.enabled) {
    return {
      status: "disabled",
      scheduledCount: 0,
      permission: await getReminderPermissionStatus(env),
    };
  }

  const permission = await requestReminderPermission(env);
  if (permission !== "granted") {
    return {
      status: "permission_denied",
      scheduledCount: 0,
      permission,
    };
  }

  const notifications = buildReminderNotifications(normalized, habits);
  if (notifications.length === 0) {
    return {
      status: "no_matching_habits",
      scheduledCount: 0,
      permission,
    };
  }

  await resolvedEnv.notifications.schedule({ notifications });
  return {
    status: "scheduled",
    scheduledCount: notifications.length,
    permission,
  };
}
