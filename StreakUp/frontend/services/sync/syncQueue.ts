import {
  DB_KEYS,
  type PendingOperation,
  dbRead,
  dbWrite,
} from "@/services/storage/offlineDb";

function readOps(): PendingOperation[] {
  return dbRead<PendingOperation[]>(DB_KEYS.pendingOps, []);
}

function writeOps(ops: PendingOperation[]): void {
  dbWrite(DB_KEYS.pendingOps, ops);
}

function nowIso(): string {
  return new Date().toISOString();
}

function updateOp(
  op: PendingOperation,
  updates: Partial<PendingOperation>,
): PendingOperation {
  return {
    ...op,
    ...updates,
    updatedAt: nowIso(),
  };
}

function makeId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

/**
 * Enqueue a toggle_checkin op, or cancel an existing one for the same
 * (habitId, date, userId) pair so double-toggles leave a clean queue.
 */
export function enqueueOrCancelToggleCheckin(
  habitId: number,
  date: string,
  userId: number,
): "enqueued" | "cancelled" {
  const ops = readOps();
  const existingIndex = ops.findIndex(
    (op) =>
      op.kind === "toggle_checkin" &&
      op.userId === userId &&
      op.payload.habit_id === habitId &&
      op.payload.date === date,
  );

  if (existingIndex >= 0) {
    ops.splice(existingIndex, 1);
    writeOps(ops);
    return "cancelled";
  }

  ops.push({
    id: makeId(),
    kind: "toggle_checkin",
    userId,
    payload: { habit_id: habitId, date },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    status: "pending",
    attemptCount: 0,
  });
  writeOps(ops);
  return "enqueued";
}

export function dequeuePendingOp(id: string): void {
  writeOps(readOps().filter((op) => op.id !== id));
}

export function getPendingOps(userId: number): PendingOperation[] {
  return readOps().filter((op) => op.userId === userId && op.status !== "failed_permanent");
}

export function getPendingOpsCount(userId: number): number {
  return getPendingOps(userId).length;
}

export function getSyncableOps(userId: number): PendingOperation[] {
  return readOps().filter((op) => op.userId === userId && (op.status ?? "pending") === "pending");
}

export function markOpsInFlight(ids: string[]): PendingOperation[] {
  const idSet = new Set(ids);
  const ops = readOps().map((op) => {
    if (!idSet.has(op.id)) {
      return op;
    }
    return updateOp(op, {
      status: "in_flight",
      attemptCount: (op.attemptCount ?? 0) + 1,
      lastError: undefined,
    });
  });
  writeOps(ops);
  return ops.filter((op) => idSet.has(op.id));
}

export function markOpsPending(ids: string[], message?: string): void {
  const idSet = new Set(ids);
  writeOps(
    readOps().map((op) =>
      idSet.has(op.id)
        ? updateOp(op, { status: "pending", lastError: message })
        : op,
    ),
  );
}

export function markOpFailedPermanent(id: string, message: string): void {
  writeOps(
    readOps().map((op) =>
      op.id === id
        ? updateOp(op, { status: "failed_permanent", lastError: message })
        : op,
    ),
  );
}

export function resetInFlightOps(userId?: number): void {
  writeOps(
    readOps().map((op) => {
      const shouldReset =
        (op.status ?? "pending") === "in_flight" &&
        (userId === undefined || op.userId === userId);
      return shouldReset ? updateOp(op, { status: "pending" }) : op;
    }),
  );
}

export function hasPendingCheckin(habitId: number, date: string, userId: number): boolean {
  return getPendingOps(userId).some(
    (op) =>
      op.kind === "toggle_checkin" &&
      op.payload.habit_id === habitId &&
      op.payload.date === date,
  );
}
