import { getStoredSession } from "@/services/auth/session";

const pages = new Map<string, unknown>();

function pageKey(page: string): string | null {
  const userId = getStoredSession()?.user.id;
  return userId ? `${userId}:${page}` : null;
}

export function readPageMemory<T>(page: string): T | null {
  const key = pageKey(page);
  return key ? (pages.get(key) as T | undefined) ?? null : null;
}

export function writePageMemory<T>(page: string, value: T): void {
  const key = pageKey(page);
  if (key) pages.set(key, value);
}

export function removePageMemory(page: string): void {
  const key = pageKey(page);
  if (key) pages.delete(key);
}

export function clearPageMemory(): void {
  pages.clear();
}
