export const SCHEMA_VERSION = 1;
export const SCHEMA_VERSION_KEY = "streakup.schema.version";

export const DB_KEYS = {
  habits: "streakup.local.habits",
  checkins: "streakup.local.checkins",
  pomodoroSessions: "streakup.local.pomodoroSessions",
  pendingOps: "streakup.local.pendingOps",
} as const;

export type DbKey = (typeof DB_KEYS)[keyof typeof DB_KEYS];

export type PendingOperationKind =
  | "create_habit"
  | "update_habit"
  | "delete_habit"
  | "toggle_checkin"
  | "create_pomodoro"
  | "complete_pomodoro";

export type PendingOperationStatus = "pending" | "in_flight" | "failed_permanent";

export interface PendingOperation {
  id: string;
  kind: PendingOperationKind;
  userId: number;
  payload: Record<string, unknown>;
  createdAt: string;
  updatedAt?: string;
  status?: PendingOperationStatus;
  attemptCount?: number;
  lastError?: string;
}

export class OfflineStorageError extends Error {
  readonly kind: "corrupt" | "quota";

  constructor(kind: "corrupt" | "quota", message: string) {
    super(message);
    this.name = "OfflineStorageError";
    this.kind = kind;
  }
}

export function canUseStorage(): boolean {
  return typeof window !== "undefined";
}

export function dbRead<T>(key: string, fallback: T): T {
  if (!canUseStorage()) {
    return fallback;
  }

  const raw = window.localStorage.getItem(key);
  if (raw === null) {
    return fallback;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    try {
      window.localStorage.removeItem(key);
    } catch {
      // ignore — best-effort quarantine
    }
    return fallback;
  }
}

export function dbWrite<T>(key: string, value: T): void {
  if (!canUseStorage()) {
    return;
  }

  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (err) {
    if (
      err instanceof DOMException &&
      (err.name === "QuotaExceededError" || err.name === "NS_ERROR_DOM_QUOTA_REACHED")
    ) {
      throw new OfflineStorageError("quota", `Storage quota exceeded writing key "${key}".`);
    }
    throw err;
  }
}

export function getSchemaVersion(): number {
  if (!canUseStorage()) {
    return 0;
  }
  const raw = window.localStorage.getItem(SCHEMA_VERSION_KEY);
  if (raw === null) {
    return 0;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function setSchemaVersion(version: number): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.setItem(SCHEMA_VERSION_KEY, String(version));
}

export function clearOfflineData(): void {
  if (!canUseStorage()) {
    return;
  }

  for (const key of Object.values(DB_KEYS)) {
    window.localStorage.removeItem(key);
  }
  window.localStorage.removeItem(SCHEMA_VERSION_KEY);
}
