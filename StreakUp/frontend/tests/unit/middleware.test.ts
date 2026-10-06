import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import {
  getAuthRedirectTarget,
  isOfflineBuildMode,
  resolveRequestAuthDecision,
} from "@/services/auth/requestProtection";

const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;

function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
}

beforeEach(() => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "false";
});

afterEach(() => {
  if (originalOfflineMode === undefined) {
    delete process.env.NEXT_PUBLIC_OFFLINE_MODE;
  } else {
    process.env.NEXT_PUBLIC_OFFLINE_MODE = originalOfflineMode;
  }
});

test("request-time auth redirects unauthenticated dashboard requests before hydration", () => {
  const decision = resolveRequestAuthDecision({
    pathname: "/habits",
    search: "?filter=today",
    accessToken: null,
    offlineMode: false,
  });

  assert.deepEqual(decision, {
    kind: "redirect_to_login",
    nextPath: "/habits?filter=today",
  });
});

test("request-time auth allows authenticated dashboard requests", () => {
  const token = buildJwt({ sub: "7", exp: Math.floor(Date.now() / 1000) + 3600 });
  const decision = resolveRequestAuthDecision({
    pathname: "/habits",
    search: "",
    accessToken: token,
    offlineMode: false,
  });

  assert.deepEqual(decision, { kind: "allow" });
});

test("request-time auth skips redirects when offline mode is explicitly enabled", () => {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "true";

  assert.equal(isOfflineBuildMode(), true);
  assert.deepEqual(
    resolveRequestAuthDecision({
      pathname: "/habits",
      search: "",
      accessToken: null,
    }),
    { kind: "allow" },
  );
});

test("getAuthRedirectTarget preserves deep links", () => {
  assert.equal(getAuthRedirectTarget("/", ""), "/");
  assert.equal(getAuthRedirectTarget("/habits", "?filter=today"), "/habits?filter=today");
});
