/**
 * accountService
 *
 * Handles account-level actions for the authenticated user.
 */

import { apiDelete, apiGet, API_ENDPOINTS } from "@/services/api/client";
import { clearOfflineData } from "@/services/storage/offlineDb";

export interface DeleteAccountResponse {
  message: string;
}

export interface AccountExport {
  profile: Record<string, unknown>;
  habits: Array<Record<string, unknown>>;
  checkins: Array<Record<string, unknown>>;
  pomodoro_sessions: Array<Record<string, unknown>>;
  achievements: Array<Record<string, unknown>>;
  xp_logs: Array<Record<string, unknown>>;
  social_memberships: Array<Record<string, unknown>>;
  owned_social_groups: Array<Record<string, unknown>>;
  validation_records: Array<Record<string, unknown>>;
}

/**
 * Permanently deletes the authenticated user's account and all their data.
 * The caller is responsible for clearing the session and redirecting
 * after this resolves successfully.
 */
export async function deleteAccount(): Promise<DeleteAccountResponse> {
  return apiDelete<DeleteAccountResponse>(API_ENDPOINTS.user.delete);
}

export async function exportAccountData(): Promise<AccountExport> {
  return apiGet<AccountExport>(API_ENDPOINTS.user.export);
}

export function clearAccountLocalData(): void {
  clearOfflineData();
}
