import { apiPost, API_ENDPOINTS, isAppErrorCode } from "@/services/api/client";
import {
  clearStoredSession,
  getStoredSession,
  getStoredAccessToken,
  hasStoredSession,
  persistSession,
  updateStoredUser,
} from "@/services/auth/session";
import { DB_KEYS, dbWrite } from "@/services/storage/offlineDb";
import type { AuthSession, AuthUser } from "@/types/auth";

const OFFLINE_LOGIN_ERROR = "No hay conexión. Usa una sesión guardada previamente.";
const OFFLINE_REGISTER_ERROR = "No hay conexión. El registro requiere internet.";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: number;
    username: string;
    email: string;
    role: string;
    created_at: string;
  };
}

export interface RegisterResponse {
  message: string;
  user: {
    id: number;
    username: string;
    email: string;
    role: string;
    created_at: string;
  };
}

/**
 * Authenticate a user and receive JWT tokens.
 */
export async function login(payload: LoginPayload): Promise<LoginResponse> {
  try {
    return await apiPost<LoginResponse>(API_ENDPOINTS.auth.login, JSON.stringify(payload), {
      headers: { Authorization: "" },
    });
  } catch (error) {
    if (isAppErrorCode(error, "network_unavailable") || isAppErrorCode(error, "backend_unavailable")) {
      throw new Error(OFFLINE_LOGIN_ERROR);
    }
    throw error;
  }
}

/**
 * Register a new user account.
 */
export async function register(payload: RegisterPayload): Promise<RegisterResponse> {
  try {
    return await apiPost<RegisterResponse>(API_ENDPOINTS.auth.register, JSON.stringify(payload), {
      headers: { Authorization: "" },
    });
  } catch (error) {
    if (isAppErrorCode(error, "network_unavailable") || isAppErrorCode(error, "backend_unavailable")) {
      throw new Error(OFFLINE_REGISTER_ERROR);
    }
    throw error;
  }
}

/**
 * Save auth session to browser storage and keep request-time auth in sync.
 */
export function saveSession(data: LoginResponse): void {
  persistSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: data.user,
  });
}

/**
 * Get current session from browser storage.
 */
export function getSession(): AuthSession | null {
  return getStoredSession();
}

/**
 * Clear auth session from browser storage.
 */
export function clearSession(): void {
  clearStoredSession();
}

export function updateSessionUser(user: AuthUser): void {
  updateStoredUser(user);
}

export function hasSavedSession(): boolean {
  return hasStoredSession();
}

/**
 * Full logout: revokes the server-side token, clears credentials, and wipes
 * all local offline caches and pending sync operations.
 */
export async function logoutAndClear(): Promise<void> {
  const token = getStoredAccessToken();
  if (token) {
    try {
      await apiPost(API_ENDPOINTS.auth.logout);
    } catch {
      // Best-effort server revocation — always clear local state regardless.
    }
  }

  clearStoredSession();

  // Wipe offline caches so the next user starts with a clean slate.
  for (const key of Object.values(DB_KEYS)) {
    try {
      dbWrite(key, []);
    } catch {
      // Quota errors are ignored during logout cleanup.
    }
  }
}

/**
 * Exchange a stored refresh token for a fresh access token.
 * Clears the session if the refresh token is missing or rejected.
 */
export async function refreshAccessToken(): Promise<string | null> {
  const { getCredentialStore } = await import("@/services/auth/credentialProvider");
  const refreshToken = getCredentialStore().get("refresh_token");

  if (!refreshToken) {
    return null;
  }

  try {
    const result = await apiPost<{ access_token: string }>(
      API_ENDPOINTS.auth.refresh,
      JSON.stringify({ refresh_token: refreshToken }),
      { headers: { Authorization: "" } },
    );
    getCredentialStore().set("access_token", result.access_token);
    return result.access_token;
  } catch {
    clearStoredSession();
    return null;
  }
}
