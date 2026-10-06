import assert from "node:assert/strict";
import test from "node:test";

import { getStatsViewState } from "@/services/stats/statsViewState";

test("getStatsViewState returns empty when there are no active habits", () => {
  const state = getStatsViewState({
    summary: {
      total_habits: 0,
    },
  });

  assert.equal(state.kind, "empty");
});

test("getStatsViewState returns error when the request fails", () => {
  const state = getStatsViewState(null, "backend unavailable");

  assert.equal(state.kind, "error");
  assert.equal(state.message, "backend unavailable");
});

test("getStatsViewState returns ready when real stats exist", () => {
  const state = getStatsViewState({
    summary: {
      total_habits: 3,
    },
  });

  assert.deepEqual(state, { kind: "ready" });
});
