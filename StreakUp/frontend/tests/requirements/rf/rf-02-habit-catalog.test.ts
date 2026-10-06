import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { fetchHabitCatalog } from "@/services/habits/habitService";
import { installBrowserTestEnv, restoreBrowserTestEnv } from "../test-utils";

// Requirement mapping:
// RF-02: Authenticated users can retrieve the habit catalog.

beforeEach(installBrowserTestEnv);
afterEach(restoreBrowserTestEnv);

test("RF-02 habit catalog is requested from the catalog endpoint", async () => {
  globalThis.fetch = async (input, init) => {
    assert.equal(input, "/api/habits/catalog");
    assert.equal(init?.method, "GET");

    return new Response(
      JSON.stringify([
        {
          id: 1,
          name: "Tomar agua",
          description: "Beber agua diariamente",
          difficulty: "facil",
          xp_base: 10,
          active: true,
        },
      ]),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };

  const catalog = await fetchHabitCatalog();

  assert.equal(catalog.length, 1);
  assert.equal(catalog[0]?.name, "Tomar agua");
});
