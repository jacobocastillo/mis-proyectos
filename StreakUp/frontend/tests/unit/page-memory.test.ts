import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { resetCredentialStore, setCredentialStore } from "@/services/auth/credentialProvider";
import { clearPageMemory, readPageMemory, writePageMemory } from "@/services/navigation/pageMemory";

const originalWindow = globalThis.window;
const credentials = new Map<string, string>();
const storage = new Map<string, string>();

function token(userId: number): string {
  const header = Buffer.from("{}").toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: String(userId), exp: Math.floor(Date.now() / 1000) + 3600 })).toString("base64url");
  return `${header}.${payload}.signature`;
}

function switchUser(id: number): void {
  credentials.set("access_token", token(id));
  storage.set("user", JSON.stringify({ id, username: `user${id}`, email: `user${id}@example.com`, role: "user" }));
}

test("page selections survive navigation and stay scoped to the signed-in user", () => {
  setCredentialStore({
    get: (key) => credentials.get(key) ?? null,
    set: (key, value) => { credentials.set(key, value); },
    remove: (key) => { credentials.delete(key); },
    clear: (keys) => keys.forEach((key) => credentials.delete(key)),
  });
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { localStorage: { getItem: (key: string) => storage.get(key) ?? null, removeItem: (key: string) => storage.delete(key) }, location: { protocol: "http:" } },
  });

  switchUser(1);
  writePageMemory("habits/new", { selectedHabitId: 7 });
  assert.deepEqual(readPageMemory("habits/new"), { selectedHabitId: 7 });

  switchUser(2);
  assert.equal(readPageMemory("habits/new"), null);
  writePageMemory("habits/new", { selectedHabitId: 9 });

  switchUser(1);
  assert.deepEqual(readPageMemory("habits/new"), { selectedHabitId: 7 });
  clearPageMemory();
  assert.equal(readPageMemory("habits/new"), null);
});

afterEach(() => {
  clearPageMemory();
  credentials.clear();
  storage.clear();
  resetCredentialStore();
  Object.defineProperty(globalThis, "window", { configurable: true, value: originalWindow });
});
