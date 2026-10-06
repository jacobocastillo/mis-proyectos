import { resetCredentialStore } from "@/services/auth/credentialProvider";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalOfflineMode = process.env.NEXT_PUBLIC_OFFLINE_MODE;
const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

export function createStorage(): Storage {
  const store = new Map<string, string>();

  return {
    clear() {
      store.clear();
    },
    getItem(key) {
      return store.get(key) ?? null;
    },
    key(index) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
    removeItem(key) {
      store.delete(key);
    },
    setItem(key, value) {
      store.set(key, String(value));
    },
  };
}

export function installBrowserTestEnv(): void {
  process.env.NEXT_PUBLIC_OFFLINE_MODE = "";
  process.env.NEXT_PUBLIC_API_URL = "";

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      localStorage: createStorage(),
      sessionStorage: createStorage(),
      location: { href: "" },
    },
  });

  let cookie = "";
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: {
      get cookie() {
        return cookie;
      },
      set cookie(value: string) {
        cookie = value;
      },
    },
  });
}

export function restoreBrowserTestEnv(): void {
  globalThis.fetch = originalFetch;
  resetCredentialStore();

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: originalDocument,
  });

  if (originalOfflineMode === undefined) {
    delete process.env.NEXT_PUBLIC_OFFLINE_MODE;
  } else {
    process.env.NEXT_PUBLIC_OFFLINE_MODE = originalOfflineMode;
  }

  if (originalApiBaseUrl === undefined) {
    delete process.env.NEXT_PUBLIC_API_URL;
  } else {
    process.env.NEXT_PUBLIC_API_URL = originalApiBaseUrl;
  }
}

export function buildJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
}
