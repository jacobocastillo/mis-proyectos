import { getStoredAccessToken } from "@/services/auth/session";
import { isOfflineModeActive } from "@/services/config/runtime";

type CacheEntry = { value: unknown; savedAt: number };
const entries = new Map<string, CacheEntry>();
const pending = new Map<string, Promise<unknown>>();
const FRESH_MS = 15_000;
let version = 0;

function key(path: string): string | null {
  if (isOfflineModeActive()) return null;
  const token = getStoredAccessToken();
  return token ? `${token}:${path}` : null;
}

export function getCachedApiData<T>(path: string): T | null {
  const cacheKey = key(path);
  const entry = cacheKey ? entries.get(cacheKey) : undefined;
  if (!entry || new Date(entry.savedAt).toDateString() !== new Date().toDateString()) return null;
  return (entry.value as T | undefined) ?? null;
}

export function hasFreshApiData(path: string): boolean {
  const cacheKey = key(path);
  const entry = cacheKey ? entries.get(cacheKey) : undefined;
  return Boolean(entry && new Date(entry.savedAt).toDateString() === new Date().toDateString() && Date.now() - entry.savedAt < FRESH_MS);
}

export function cachedApiRequest<T>(path: string, fetcher: () => Promise<T>): Promise<T> {
  const cacheKey = key(path);
  if (!cacheKey) return fetcher();
  const entry = entries.get(cacheKey);
  if (entry && new Date(entry.savedAt).toDateString() === new Date().toDateString() && Date.now() - entry.savedAt < FRESH_MS) return Promise.resolve(entry.value as T);
  const inFlight = pending.get(cacheKey);
  if (inFlight) return inFlight as Promise<T>;

  const startedAtVersion = version;
  const request = fetcher().then((value) => {
    if (version === startedAtVersion) entries.set(cacheKey, { value, savedAt: Date.now() });
    return value;
  }).finally(() => {
    if (pending.get(cacheKey) === request) pending.delete(cacheKey);
  });
  pending.set(cacheKey, request);
  return request;
}

export function clearApiCache(): void {
  version += 1;
  entries.clear();
  pending.clear();
}
