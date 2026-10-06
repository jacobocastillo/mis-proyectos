import { DB_KEYS, SCHEMA_VERSION, canUseStorage, dbRead, dbWrite, getSchemaVersion, setSchemaVersion } from "./offlineDb";

export function runMigrationsOnce(): void {
  if (getSchemaVersion() >= SCHEMA_VERSION) {
    return;
  }

  if (!canUseStorage()) {
    return;
  }

  // v0 → v1: re-parse (and quarantine corrupt) existing cache arrays; leave absent keys absent
  for (const key of [DB_KEYS.habits, DB_KEYS.checkins, DB_KEYS.pomodoroSessions] as const) {
    if (window.localStorage.getItem(key) !== null) {
      dbWrite(key, dbRead(key, []));
    }
  }

  // pendingOps must always exist so no queued op is lost across page reloads
  dbWrite(DB_KEYS.pendingOps, dbRead(DB_KEYS.pendingOps, []));

  setSchemaVersion(SCHEMA_VERSION);
}
