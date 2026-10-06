import { apiPost, API_ENDPOINTS, isAppErrorCode } from "@/services/api/client";
import { getSession } from "@/services/auth/authService";
import { syncLocalCheckinResult } from "@/services/storage/localData";
import type { PendingOperation } from "@/services/storage/offlineDb";
import {
  dequeuePendingOp,
  getSyncableOps,
  markOpFailedPermanent,
  markOpsInFlight,
  markOpsPending,
  resetInFlightOps,
} from "@/services/sync/syncQueue";
import type { CheckinToggleResult } from "@/types/checkins";

interface SyncOperationRequest {
  client_operation_id: string;
  operation_type: PendingOperation["kind"];
  payload: Record<string, unknown>;
  created_at: string;
}

interface SyncOperationError {
  code: string;
  message: string;
  retryable?: boolean;
}

interface SyncOperationResult {
  client_operation_id: string;
  operation_type: string;
  status: "acked" | "failed" | "conflict" | "retry";
  result?: CheckinToggleResult | null;
  error?: SyncOperationError | null;
}

interface SyncPushResponse {
  results: SyncOperationResult[];
}

export interface SyncDrainResult {
  attempted: number;
  acked: number;
  failed: number;
  retryable: number;
}

let drainInProgress = false;

function getCurrentUserId(): number {
  const session = getSession();
  const userId = Number(session?.user.id ?? 0);
  return Number.isFinite(userId) ? userId : 0;
}

function toRequestOperation(op: PendingOperation): SyncOperationRequest {
  return {
    client_operation_id: op.id,
    operation_type: op.kind,
    payload: op.payload,
    created_at: op.createdAt,
  };
}

function isRetryableSyncError(error: unknown): boolean {
  return (
    isAppErrorCode(error, "network_unavailable") ||
    isAppErrorCode(error, "backend_unavailable") ||
    isAppErrorCode(error, "offline_mode")
  );
}

export async function drainSyncQueue(userId = getCurrentUserId()): Promise<SyncDrainResult> {
  if (userId <= 0 || drainInProgress) {
    return { attempted: 0, acked: 0, failed: 0, retryable: 0 };
  }

  const pendingOps = getSyncableOps(userId);
  if (pendingOps.length === 0) {
    return { attempted: 0, acked: 0, failed: 0, retryable: 0 };
  }

  drainInProgress = true;
  const operationIds = pendingOps.map((op) => op.id);
  markOpsInFlight(operationIds);

  try {
    const response = await apiPost<SyncPushResponse>(
      API_ENDPOINTS.sync.push,
      JSON.stringify({ operations: pendingOps.map(toRequestOperation) }),
    );

    let acked = 0;
    let failed = 0;
    let retryable = 0;

    const seenIds = new Set<string>();
    for (const result of response.results) {
      seenIds.add(result.client_operation_id);

      if (result.status === "acked") {
        if (result.operation_type === "toggle_checkin" && result.result) {
          syncLocalCheckinResult(result.result, userId);
        }
        dequeuePendingOp(result.client_operation_id);
        acked += 1;
        continue;
      }

      if (result.status === "retry" || result.error?.retryable) {
        markOpsPending([result.client_operation_id], result.error?.message);
        retryable += 1;
        continue;
      }

      markOpFailedPermanent(
        result.client_operation_id,
        result.error?.message ?? "La operación no pudo sincronizarse.",
      );
      failed += 1;
    }

    const missingIds = operationIds.filter((id) => !seenIds.has(id));
    if (missingIds.length > 0) {
      markOpsPending(missingIds, "El servidor no devolvió confirmación para la operación.");
      retryable += missingIds.length;
    }

    return { attempted: pendingOps.length, acked, failed, retryable };
  } catch (error) {
    if (isRetryableSyncError(error)) {
      markOpsPending(operationIds, error instanceof Error ? error.message : undefined);
      return { attempted: pendingOps.length, acked: 0, failed: 0, retryable: pendingOps.length };
    }

    markOpsPending(operationIds, error instanceof Error ? error.message : undefined);
    throw error;
  } finally {
    drainInProgress = false;
  }
}

export function recoverInterruptedSync(userId = getCurrentUserId()): void {
  resetInFlightOps(userId > 0 ? userId : undefined);
}
