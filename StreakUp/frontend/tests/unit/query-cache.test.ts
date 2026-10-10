import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { cachedApiRequest, clearApiCache, getCachedApiData } from "@/services/api/queryCache";
import { setCredentialStore } from "@/services/auth/credentialProvider";
import { apiPost } from "@/services/api/client";

const credentials = new Map<string, string>();
const originalFetch = globalThis.fetch;
setCredentialStore({
  get: (key) => credentials.get(key) ?? null,
  set: (key, value) => { credentials.set(key, value); },
  remove: (key) => { credentials.delete(key); },
  clear: (keys) => keys.forEach((key) => credentials.delete(key)),
});

afterEach(() => {
  clearApiCache();
  credentials.clear();
  globalThis.fetch = originalFetch;
});

test("a successful check-in invalidates cached dashboard reads", async () => {
  credentials.set("access_token", "user-one-token");
  await cachedApiRequest("/api/stats/summary", async () => ({ streak: 2 }));
  assert.deepEqual(getCachedApiData("/api/stats/summary"), { streak: 2 });

  globalThis.fetch = async () => new Response(JSON.stringify({ checked: true }), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
  await apiPost("/api/checkins/toggle", JSON.stringify({ habit_id: 1 }));
  assert.equal(getCachedApiData("/api/stats/summary"), null);
});

test("deduplicates reads and keeps cached data separate by session", async () => {
  credentials.set("access_token", "user-one-token");
  let requests = 0;
  const fetcher = async () => {
    requests += 1;
    return [{ id: requests }];
  };

  const [first, second] = await Promise.all([
    cachedApiRequest("/api/habits", fetcher),
    cachedApiRequest("/api/habits", fetcher),
  ]);
  assert.equal(requests, 1);
  assert.deepEqual(first, second);
  assert.deepEqual(getCachedApiData("/api/habits"), [{ id: 1 }]);

  credentials.set("access_token", "user-two-token");
  assert.equal(getCachedApiData("/api/habits"), null);
  await cachedApiRequest("/api/habits", fetcher);
  assert.equal(requests, 2);

  clearApiCache();
  assert.equal(getCachedApiData("/api/habits"), null);
});
