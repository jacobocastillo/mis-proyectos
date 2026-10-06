import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { fetchHabitHistory } from "@/services/history/historyService";
import { persistSession, clearStoredSession } from "@/services/auth/session";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

function createTestJwt(): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(
    JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }),
  ).toString("base64url");
  return `${header}.${payload}.signature`;
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

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_URL = "http://localhost:5000";
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      localStorage: createStorage(),
      location: { href: "" },
    },
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: { cookie: "" },
  });
  persistSession({
    accessToken: createTestJwt(),
    user: {
      id: 7,
      username: "tester",
      email: "tester@example.com",
      role: "user",
    },
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  clearStoredSession();
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: originalDocument,
  });
  if (originalApiBaseUrl === undefined) {
    delete process.env.NEXT_PUBLIC_API_URL;
  } else {
    process.env.NEXT_PUBLIC_API_URL = originalApiBaseUrl;
  }
});

test("fetchHabitHistory sends filters to the history endpoint", async () => {
  globalThis.fetch = async (input, init) => {
    assert.equal(
      String(input),
      "http://localhost:5000/api/checkins/history?from=2026-05-01&to=2026-05-03&habit_id=9&status=rejected&limit=10&cursor=20",
    );
    assert.equal(init?.method, "GET");

    return new Response(
      JSON.stringify({
        items: [
          {
            id: "validation:1",
            source: "validation",
            habit_id: 9,
            catalog_habit_id: 2,
            habit_name: "Deep work",
            category_id: 1,
            category_name: "Productividad",
            event_date: "2026-05-03",
            occurred_at: "2026-05-03T16:00:00+00:00",
            status: "rejected",
            validation_type: "photo",
            xp_awarded: 0,
            validation_id: 1,
            checkin_id: null,
            reason: "not enough evidence",
            confidence: 0.2,
          },
        ],
        next_cursor: null,
      }),
      {
        status: 200,
        headers: { "content-type": "application/json" },
      },
    );
  };

  const result = await fetchHabitHistory({
    from: "2026-05-01",
    to: "2026-05-03",
    habit_id: 9,
    status: "rejected",
    limit: 10,
    cursor: "20",
  });

  assert.equal(result.items.length, 1);
  assert.equal(result.items[0]?.status, "rejected");
});
