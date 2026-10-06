import { apiDelete, apiGet, apiPost, API_ENDPOINTS, shouldUseOfflineFallback } from "@/services/api/client";
import type {
  CreateSharedGroupPayload,
  JoinSharedGroupPayload,
  SharedStreakGroup,
} from "@/types/social";

function offlineSocialError(): Error {
  return new Error("Las rachas compartidas requieren conexión con el servidor.");
}

export async function fetchSharedGroups(): Promise<SharedStreakGroup[]> {
  try {
    return await apiGet<SharedStreakGroup[]>(API_ENDPOINTS.social.groups);
  } catch (error) {
    if (shouldUseOfflineFallback(error)) {
      throw offlineSocialError();
    }
    throw error;
  }
}

export async function createSharedGroup(payload: CreateSharedGroupPayload): Promise<SharedStreakGroup> {
  try {
    return await apiPost<SharedStreakGroup>(
      API_ENDPOINTS.social.groups,
      JSON.stringify(payload),
    );
  } catch (error) {
    if (shouldUseOfflineFallback(error)) {
      throw offlineSocialError();
    }
    throw error;
  }
}

export async function joinSharedGroup(payload: JoinSharedGroupPayload): Promise<SharedStreakGroup> {
  try {
    return await apiPost<SharedStreakGroup>(
      API_ENDPOINTS.social.join,
      JSON.stringify(payload),
    );
  } catch (error) {
    if (shouldUseOfflineFallback(error)) {
      throw offlineSocialError();
    }
    throw error;
  }
}

export async function fetchSharedGroup(id: number): Promise<SharedStreakGroup> {
  return apiGet<SharedStreakGroup>(API_ENDPOINTS.social.detail(id));
}

export async function leaveSharedGroup(id: number): Promise<void> {
  await apiDelete<void>(API_ENDPOINTS.social.membership(id));
}
