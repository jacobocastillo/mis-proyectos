import { Capacitor } from "@capacitor/core";

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);
const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

export class ApiBaseUrlConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiBaseUrlConfigurationError";
  }
}

function readOfflineFlag(): string {
  return (process.env.NEXT_PUBLIC_OFFLINE_MODE ?? "").trim().toLowerCase();
}

export function isOfflineModeEnabled(): boolean {
  return TRUE_VALUES.has(readOfflineFlag());
}

export function isOfflineModeActive(): boolean {
  return isOfflineModeEnabled();
}

export function isConnectedModeActive(): boolean {
  return !isOfflineModeEnabled();
}

export function isNativeApp(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  return Capacitor.isNativePlatform();
}

export function getApiBaseUrl(): string {
  const value = (process.env.NEXT_PUBLIC_API_URL ?? "").trim();
  const nodeEnv = (process.env.NODE_ENV ?? "").trim().toLowerCase();

  if (!value) {
    if (isNativeApp()) {
      throw new ApiBaseUrlConfigurationError(
        "Configura NEXT_PUBLIC_API_URL con una IP local accesible, por ejemplo http://192.168.1.50:5000.",
      );
    }

    if (nodeEnv && nodeEnv !== "development" && nodeEnv !== "test") {
      throw new ApiBaseUrlConfigurationError(
        "NEXT_PUBLIC_API_URL es obligatorio para builds conectados fuera de desarrollo.",
      );
    }

    return "";
  }

  let url: URL;

  try {
    url = new URL(value);
  } catch {
    throw new ApiBaseUrlConfigurationError(
      "NEXT_PUBLIC_API_URL debe ser una URL absoluta valida.",
    );
  }

  if (isNativeApp() && LOOPBACK_HOSTS.has(url.hostname.toLowerCase())) {
    throw new ApiBaseUrlConfigurationError(
      "NEXT_PUBLIC_API_URL no puede usar localhost en la app movil. Usa una IP local accesible, por ejemplo http://192.168.1.50:5000.",
    );
  }

  return value.replace(/\/+$/, "");
}
