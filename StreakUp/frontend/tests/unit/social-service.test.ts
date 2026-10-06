import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { saveSession } from "@/services/auth/authService";
import {
  createSharedGroup,
  fetchSharedGroups,
  joinSharedGroup,
  leaveSharedGroup,
} from "@/services/social/socialService";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;
const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
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

function makeGroupResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 4,
    name: "Equipo",
    invite_code: "ABC123",
    owner_user_id: 7,
    habit_id: 12,
    habit_name: "Meditar",
    max_participants: 3,
    member_count: 2,
    start_date: "2026-05-10",
    duration_days: null,
    end_date: null,
    group_status: "active",
    winner_user_id: null,
    created_at: "2026-05-03T00:00:00Z",
    shared_streak: {
      current: 3,
      today_completed_members: 2,
      required_members: 2,
      ready: true,
    },
    members: [],
    ...overrides,
  };
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

  saveSession({
    access_token: buildJwt({ sub: "7", exp: Math.floor(Date.now() / 1000) + 3600 }),
    refresh_token: "saved-refresh",
    user: {
      id: 7,
      username: "alice",
      email: "alice@example.com",
      role: "user",
      created_at: "2026-04-05T00:00:00Z",
    },
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;

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

test("social service creates and joins groups through social endpoints", async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = async (input, init) => {
    calls.push({ url: String(input), init });
    return new Response(
      JSON.stringify(makeGroupResponse()),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };

  const created = await createSharedGroup({ name: "Equipo", user_habit_id: 5 });
  const joined = await joinSharedGroup({ invite_code: "ABC123" });

  assert.equal(calls[0]?.url.endsWith("/api/social/groups"), true);
  assert.equal(calls[0]?.init?.body, JSON.stringify({ name: "Equipo", user_habit_id: 5 }));
  assert.equal(calls[1]?.url.endsWith("/api/social/groups/join"), true);
  assert.equal(calls[1]?.init?.body, JSON.stringify({ invite_code: "ABC123" }));
  assert.equal(created.shared_streak.current, 3);
  assert.equal(joined.member_count, 2);
});

test("createSharedGroup forwards user_habit_id in request body", async () => {
  let capturedBody: unknown;
  globalThis.fetch = async (_input, init) => {
    capturedBody = JSON.parse(init?.body as string);
    return new Response(JSON.stringify(makeGroupResponse()), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  await createSharedGroup({ name: "Grupo test", user_habit_id: 99 });

  assert.deepEqual(capturedBody, { name: "Grupo test", user_habit_id: 99 });
});

test("createSharedGroup response includes habit_id, habit_name, and max_participants", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify(makeGroupResponse({ habit_id: 7, habit_name: "Ejercicio", max_participants: 3 })),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );

  const group = await createSharedGroup({ name: "Test", user_habit_id: 7 });

  assert.equal(group.habit_id, 7);
  assert.equal(group.habit_name, "Ejercicio");
  assert.equal(group.max_participants, 3);
});

test("social service lists and leaves groups", async () => {
  const calls: string[] = [];
  globalThis.fetch = async (input, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(input)}`);
    if (init?.method === "DELETE") {
      return new Response(JSON.stringify({ left: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  await fetchSharedGroups();
  await leaveSharedGroup(9);

  assert.equal(calls[0]?.endsWith("/api/social/groups"), true);
  assert.equal(calls[1]?.includes("DELETE"), true);
  assert.equal(calls[1]?.endsWith("/api/social/groups/9/membership"), true);
});

test("offline mode does not fabricate social success", async () => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "true";

  await assert.rejects(fetchSharedGroups(), /requieren conexión/);
  await assert.rejects(createSharedGroup({ name: "Equipo", user_habit_id: 1 }), /requieren conexión/);
});

test("fetchSharedGroups returns groups with habit_id and habit_name", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify([
        makeGroupResponse({ habit_id: 5, habit_name: "Correr" }),
        makeGroupResponse({ id: 5, habit_id: null, habit_name: null }),
      ]),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );

  const groups = await fetchSharedGroups();

  assert.equal(groups.length, 2);
  assert.equal(groups[0]?.habit_id, 5);
  assert.equal(groups[0]?.habit_name, "Correr");
  assert.equal(groups[1]?.habit_id, null);
  assert.equal(groups[1]?.habit_name, null);
});

test("createSharedGroup forwards duration_days when provided", async () => {
  let capturedBody: unknown;
  globalThis.fetch = async (_input, init) => {
    capturedBody = JSON.parse(init?.body as string);
    return new Response(
      JSON.stringify(makeGroupResponse({ duration_days: 7, end_date: "2026-05-17" })),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };

  const group = await createSharedGroup({ name: "Semana", user_habit_id: 3, duration_days: 7 });

  assert.deepEqual((capturedBody as Record<string, unknown>).duration_days, 7);
  assert.equal(group.duration_days, 7);
});

test("createSharedGroup forwards null duration_days for unlimited mode", async () => {
  let capturedBody: unknown;
  globalThis.fetch = async (_input, init) => {
    capturedBody = JSON.parse(init?.body as string);
    return new Response(JSON.stringify(makeGroupResponse()), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const group = await createSharedGroup({ name: "Sin límite", user_habit_id: 1, duration_days: null });

  assert.deepEqual((capturedBody as Record<string, unknown>).duration_days, null);
  assert.equal(group.duration_days, null);
  assert.equal(group.group_status, "active");
});

test("fetchSharedGroups returns groups with duel fields (group_status, winner_user_id)", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify([
        makeGroupResponse({ group_status: "finished", winner_user_id: 7, duration_days: 15 }),
      ]),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );

  const groups = await fetchSharedGroups();

  assert.equal(groups[0]?.group_status, "finished");
  assert.equal(groups[0]?.winner_user_id, 7);
  assert.equal(groups[0]?.duration_days, 15);
});

test("fetchSharedGroups returns members with lost and winner status", async () => {
  const members = [
    {
      user_id: 7, username: "alice", status: "winner", share_progress: true,
      joined_at: "2026-05-10T00:00:00Z", lost_at: null, today_completed: false, completed_days: 5,
    },
    {
      user_id: 8, username: "bob", status: "lost", share_progress: true,
      joined_at: "2026-05-10T00:00:00Z", lost_at: "2026-05-12T00:00:00Z", today_completed: false, completed_days: 2,
    },
  ];
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify([makeGroupResponse({ group_status: "finished", winner_user_id: 7, members })]),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );

  const groups = await fetchSharedGroups();
  const fetchedMembers = groups[0]?.members ?? [];

  assert.equal(fetchedMembers[0]?.status, "winner");
  assert.equal(fetchedMembers[0]?.completed_days, 5);
  assert.equal(fetchedMembers[1]?.status, "lost");
  assert.equal(fetchedMembers[1]?.lost_at, "2026-05-12T00:00:00Z");
});
