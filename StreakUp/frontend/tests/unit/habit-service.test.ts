import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { createHabit, fetchHabit, updateHabit } from "@/services/habits/habitService";
import { AppError } from "@/services/api/client";
import { persistSession, clearStoredSession } from "@/services/auth/session";
import { getHabitFrequencyLabel } from "@/types/habits";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;
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

beforeEach(() => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "";
  process.env.NEXT_PUBLIC_API_URL = "http://localhost:5000";
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: createWindow(),
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: createDocument(),
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

test("updateHabit uses connected API when offline mode is disabled", async () => {
  globalThis.fetch = async (_input, init) => {
    assert.equal(init?.method, "PUT");
    assert.equal(
      init?.body,
      JSON.stringify({
        custom_name: "Read fiction",
        validation_type: "texto",
        target_quantity: 20,
        target_unit: "minutes",
      }),
    );

    return new Response(
      JSON.stringify({
        id: 1,
        user_id: 7,
        catalog_habit_id: 9,
        name: "Read fiction",
        custom_name: "Read fiction",
        description: "Lectura diaria",
        custom_description: null,
        icon: "BookOpen",
        validation_type: "texto",
        habit_type: "quantity",
        frequency: "daily",
        section: "fire",
        target_duration: null,
        pomodoro_enabled: false,
        target_quantity: 20,
        target_unit: "minutes",
        created_at: "2026-04-15T00:00:00Z",
        updated_at: "2026-04-15T00:10:00Z",
      }),
      {
        status: 200,
        headers: { "content-type": "application/json" },
      },
    );
  };

  const habit = await updateHabit(1, {
    custom_name: "Read fiction",
    validation_type: "texto",
    target_quantity: 20,
    target_unit: "minutes",
  });

  assert.equal(habit.custom_name, "Read fiction");
  assert.equal(habit.validation_type, "texto");
  assert.equal(habit.target_quantity, 20);
});

test("fetchHabit uses detail endpoint and returns backend metadata", async () => {
  globalThis.fetch = async (input) => {
    assert.equal(String(input), "http://localhost:5000/api/habits/4");

    return new Response(
      JSON.stringify({
        id: 4,
        user_id: 7,
        catalog_habit_id: 6,
        name: "Deep work",
        custom_name: "Deep work",
        description: "Focus block",
        custom_description: "Focus block",
        icon: "Laptop",
        validation_type: "tiempo",
        habit_type: "time",
        frequency: "daily",
        section: "fire",
        target_duration: 50,
        pomodoro_enabled: true,
        target_quantity: null,
        target_unit: null,
        created_at: "2026-04-15T00:00:00Z",
        updated_at: "2026-04-15T00:10:00Z",
      }),
      {
        status: 200,
        headers: { "content-type": "application/json" },
      },
    );
  };

  const habit = await fetchHabit(4);

  assert.equal(habit.validation_type, "tiempo");
  assert.equal(habit.target_duration, 50);
  assert.equal(habit.custom_description, "Focus block");
});

test("createHabit sends optional metadata overrides in connected mode", async () => {
  globalThis.fetch = async (_input, init) => {
    assert.equal(init?.method, "POST");
    assert.equal(
      init?.body,
      JSON.stringify({
        habito_id: 6,
        custom_name: "Deep work",
        description: "Before lunch",
        validation_type: "tiempo",
        frequency: "daily",
        target_duration: 50,
        target_quantity: null,
        target_unit: null,
      }),
    );

    return new Response(
      JSON.stringify({
        id: 5,
        user_id: 7,
        catalog_habit_id: 6,
        name: "Deep work",
        custom_name: "Deep work",
        description: "Before lunch",
        custom_description: "Before lunch",
        icon: "Laptop",
        validation_type: "tiempo",
        habit_type: "time",
        frequency: "daily",
        section: "fire",
        target_duration: 50,
        pomodoro_enabled: true,
        target_quantity: null,
        target_unit: null,
        created_at: "2026-04-15T00:00:00Z",
        updated_at: "2026-04-15T00:10:00Z",
      }),
      {
        status: 201,
        headers: { "content-type": "application/json" },
      },
    );
  };

  const habit = await createHabit({
    habito_id: 6,
    custom_name: "Deep work",
    description: "Before lunch",
    validation_type: "tiempo",
    frequency: "daily",
    target_duration: 50,
    target_quantity: null,
    target_unit: null,
  });

  assert.equal(habit.custom_name, "Deep work");
  assert.equal(habit.validation_type, "tiempo");
});

test("updateHabit still falls back only in explicit offline mode", async () => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "true";
  const createdHabit = await createHabit({ habito_id: 1 });

  const habit = await updateHabit(createdHabit.id, {
    name: "Test",
    habit_type: "boolean",
    frequency: "daily",
    section: "fire",
  });

  assert.equal(habit.name, "Test");
});

test("updateHabit surfaces network failure in connected mode", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(
    updateHabit(1, { custom_name: "Test" }),
    (error: unknown) => error instanceof AppError && error.code === "network_unavailable",
  );
});

test("getHabitFrequencyLabel formats custom schedules explicitly", () => {
  assert.equal(getHabitFrequencyLabel("daily"), "Diaria");
  assert.equal(getHabitFrequencyLabel("weekly"), "Semanal");
  assert.equal(getHabitFrequencyLabel("custom"), "Personalizada");
  assert.equal(
    getHabitFrequencyLabel({ frequency: "custom", schedule_days: [4, 0, 2] }),
    "Personalizada: L, X, V",
  );
});
