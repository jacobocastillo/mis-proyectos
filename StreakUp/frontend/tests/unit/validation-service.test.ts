import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { saveSession } from "@/services/auth/authService";
import { validateHabit } from "@/services/validation/validationService";

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

test("validation service maps provider-unavailable responses to a controlled message", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        error: "La validación de fotos no está disponible temporalmente.",
        code: "validation_provider_unavailable",
      }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" },
      },
    );

  await assert.rejects(
    validateHabit({ habit_id: 1, image_base64: "image-base64" }),
    /La validación de fotos no está disponible temporalmente\. Inténtalo más tarde\./,
  );
});

test("validation service maps backend-unreachable failures to a friendly network message", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  await assert.rejects(
    validateHabit({ habit_id: 1, image_base64: "image-base64" }),
    /No se pudo contactar el servicio de validación/,
  );
});

test("validation service sends mime_type with the image payload", async () => {
  globalThis.fetch = async (_input, init) => {
    assert.equal(init?.method, "POST");
    assert.equal(
      init?.body,
      JSON.stringify({
        habit_id: 3,
        image_base64: "image-base64",
        mime_type: "image/png",
      }),
    );

    return new Response(
      JSON.stringify({
        valido: true,
        razon: "ok",
        confianza: 0.9,
        xp_ganado: 15,
        nueva_racha: 2,
        difficulty_recommendation: {
          level: "media",
          confidence: 0.7,
          explanation: "Buen nivel para este hábito.",
          source: "deterministic",
          advisory: true,
        },
        feedback: {
          message: "Validaste el hábito con progreso concreto.",
          tone: "progress",
          context: { today_completed: 1 },
        },
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  };

  const result = await validateHabit({
    habit_id: 3,
    image_base64: "image-base64",
    mime_type: "image/png",
  });

  assert.equal(result.valido, true);
  assert.equal(result.xp_ganado, 15);
  assert.equal(result.difficulty_recommendation?.advisory, true);
  assert.equal(result.feedback?.message, "Validaste el hábito con progreso concreto.");
});
