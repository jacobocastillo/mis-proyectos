import {
  ApiBaseUrlConfigurationError,
  getApiBaseUrl,
  isOfflineModeActive,
} from "@/services/config/runtime";
import {
  clearStoredSession,
  getStoredAccessToken,
} from "@/services/auth/session";

import { API_ENDPOINTS } from "./endpoints";

export type AppErrorCode =
  | "offline_mode"
  | "network_unavailable"
  | "backend_unavailable"
  | "auth_required"
  | "validation_error"
  | "config_error"
  | "api_error";

interface AppErrorOptions {
  status?: number;
  apiCode?: string;
  cause?: unknown;
}

export class AppError extends Error {
  readonly code: AppErrorCode;
  readonly status?: number;
  readonly apiCode?: string;

  constructor(code: AppErrorCode, message: string, options: AppErrorOptions = {}) {
    super(message);
    this.name = "AppError";
    this.code = code;
    this.status = options.status;
    this.apiCode = options.apiCode;
    (this as AppError & { cause?: unknown }).cause = options.cause;
  }
}

export class OfflineModeError extends AppError {
  constructor(message = "El modo offline está activo.") {
    super("offline_mode", message);
    this.name = "OfflineModeError";
  }
}

export interface RequestOptions extends RequestInit {
  path: string;
}

function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return getStoredAccessToken();
}

export function buildAuthHeaders(headers?: HeadersInit): HeadersInit {
  const token = getAccessToken();

  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...headers,
  };
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }

  try {
    return await response.json();
  } catch {
    return null;
  }
}

interface ApiErrorDetails {
  message: string;
  apiCode?: string;
}

export function getApiErrorMessage(errorBody: unknown, fallback: string): string {
  return getApiErrorDetails(errorBody, fallback).message;
}

function getApiErrorDetails(errorBody: unknown, fallback: string): ApiErrorDetails {
  if (typeof errorBody === "string" && errorBody.trim()) {
    return { message: errorBody };
  }

  if (errorBody && typeof errorBody === "object") {
    const candidate = errorBody as {
      code?: string;
      error?: string;
      errors?: string[];
      message?: string;
    };

    if (candidate.error) {
      return { message: candidate.error, apiCode: candidate.code };
    }

    if (candidate.message) {
      return { message: candidate.message, apiCode: candidate.code };
    }

    if (candidate.errors?.length) {
      return { message: candidate.errors.join(", "), apiCode: candidate.code };
    }
  }

  return { message: fallback };
}

function getHttpErrorCode(status: number): AppErrorCode {
  if (status === 401 || status === 403) {
    return "auth_required";
  }

  if (status === 400 || status === 409 || status === 422) {
    return "validation_error";
  }

  if (status >= 500) {
    return "backend_unavailable";
  }

  return "api_error";
}

function mapTransportError(error: unknown): AppError {
  if (error instanceof AppError) {
    return error;
  }

  if (error instanceof ApiBaseUrlConfigurationError) {
    return new AppError("config_error", error.message, { cause: error });
  }

  if (error instanceof TypeError) {
    return new AppError(
      "network_unavailable",
      "No se pudo conectar con el servidor. Verifica tu conexión e inténtalo de nuevo.",
      { cause: error },
    );
  }

  if (error instanceof Error) {
    return new AppError(
      "backend_unavailable",
      error.message || "No se pudo completar la solicitud en este momento.",
      { cause: error },
    );
  }

  return new AppError(
    "backend_unavailable",
    "No se pudo completar la solicitud en este momento.",
    { cause: error },
  );
}

function handleUnauthorized(message: string, apiCode?: string): never {
  clearStoredSession();

  if (typeof window !== "undefined") {
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  throw new AppError("auth_required", message, { status: 401, apiCode });
}

export function isAppError(error: unknown): error is AppError {
  return error instanceof AppError;
}

export function isAppErrorCode(error: unknown, code: AppErrorCode): boolean {
  return isAppError(error) && error.code === code;
}

export function shouldUseOfflineFallback(error: unknown): boolean {
  return error instanceof OfflineModeError;
}

// ─── Request timeout (ms) ────────────────────────────────────────────────────
const REQUEST_TIMEOUT_MS = 15_000;

/** Wrap a fetch call with an AbortController that times out after REQUEST_TIMEOUT_MS. */
async function fetchWithTimeout(
  url: string,
  init: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  const timerId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new AppError(
        "network_unavailable",
        "La solicitud tardó demasiado. Verifica tu conexión e inténtalo de nuevo.",
        { cause: error },
      );
    }
    throw error;
  } finally {
    clearTimeout(timerId);
  }
}

/** Try the fetch once; on a transient network error, wait briefly and retry once. */
async function fetchWithRetry(
  url: string,
  init: RequestInit,
  isNetworkError: (err: unknown) => boolean,
): Promise<Response> {
  try {
    return await fetchWithTimeout(url, init);
  } catch (firstError) {
    // Only retry on genuine network-level failures, not on app-level errors.
    if (!isNetworkError(firstError)) {
      throw firstError;
    }
    // Wait 800 ms before the single retry attempt.
    await new Promise<void>((resolve) => setTimeout(resolve, 800));
    return fetchWithTimeout(url, init);
  }
}

export async function apiRequest<T>({ path, headers, ...options }: RequestOptions): Promise<T> {
  if (isOfflineModeActive()) {
    throw new OfflineModeError();
  }

  let apiBaseUrl: string;

  try {
    apiBaseUrl = getApiBaseUrl();
  } catch (error) {
    throw mapTransportError(error);
  }

  const isRetryableNetworkError = (err: unknown): boolean =>
    err instanceof TypeError;

  let response: Response;

  try {
    response = await fetchWithRetry(
      `${apiBaseUrl}${path}`,
      { ...options, headers: buildAuthHeaders(headers) },
      isRetryableNetworkError,
    );
  } catch (error) {
    throw mapTransportError(error);
  }

  const responseBody = await parseResponseBody(response);

  if (!response.ok) {
    const details = getApiErrorDetails(
      responseBody,
      `API request failed with status ${response.status}`,
    );

    if (response.status === 401) {
      return handleUnauthorized(
        details.message || "Tu sesión expiró. Inicia sesión de nuevo.",
        details.apiCode,
      );
    }

    throw new AppError(getHttpErrorCode(response.status), details.message, {
      status: response.status,
      apiCode: details.apiCode,
    });
  }

  return responseBody as T;
}

export function apiGet<T>(path: string, options?: Omit<RequestOptions, "path" | "method">): Promise<T> {
  return apiRequest<T>({ path, method: "GET", ...options });
}

export function apiPost<T>(
  path: string,
  body?: RequestOptions["body"],
  options?: Omit<RequestOptions, "path" | "method" | "body">,
): Promise<T> {
  return apiRequest<T>({ path, method: "POST", body, ...options });
}

export function apiPut<T>(
  path: string,
  body?: RequestOptions["body"],
  options?: Omit<RequestOptions, "path" | "method" | "body">,
): Promise<T> {
  return apiRequest<T>({ path, method: "PUT", body, ...options });
}

export function apiDelete<T>(
  path: string,
  options?: Omit<RequestOptions, "path" | "method">,
): Promise<T> {
  return apiRequest<T>({ path, method: "DELETE", ...options });
}

export { API_ENDPOINTS };
