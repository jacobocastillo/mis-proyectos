import { apiGet, apiPut, API_ENDPOINTS } from "@/services/api/client";
import { updateSessionUser } from "@/services/auth/authService";
import type { AuthUser } from "@/types/auth";

export interface UpdateProfilePayload {
  username: string;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  return apiGet<AuthUser>(API_ENDPOINTS.user.me);
}

export async function updateProfile(payload: UpdateProfilePayload): Promise<AuthUser> {
  const user = await apiPut<AuthUser>(
    API_ENDPOINTS.user.update,
    JSON.stringify(payload),
  );
  updateSessionUser(user);
  return user;
}
