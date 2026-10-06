/**
 * CredentialStore — runtime-agnostic token storage abstraction.
 *
 * Web: sessionStorage (cleared on tab close; not persisted across browser restarts)
 * Native (Android): same sessionStorage backing until @capacitor-community/secure-storage-plugin
 *   is installed and wired. Upgrade path:
 *     npm install @capacitor-community/secure-storage-plugin
 *     npx cap sync android
 *   Then replace SessionStorageCredentialStore with a KeystoreCredentialStore that
 *   delegates to SecureStorage from that plugin.
 *
 * Tokens are intentionally NOT written to localStorage. Use localStorage only for
 * non-sensitive offline data (habits, checkins, pending ops).
 */

export interface CredentialStore {
  get(key: string): string | null;
  set(key: string, value: string): void;
  remove(key: string): void;
  clear(keys: string[]): void;
}

class SessionStorageCredentialStore implements CredentialStore {
  get(key: string): string | null {
    if (typeof window === "undefined") {
      return null;
    }
    return window.sessionStorage?.getItem(key) ?? null;
  }

  set(key: string, value: string): void {
    if (typeof window === "undefined") {
      return;
    }
    window.sessionStorage?.setItem(key, value);
  }

  remove(key: string): void {
    if (typeof window === "undefined") {
      return;
    }
    window.sessionStorage?.removeItem(key);
  }

  clear(keys: string[]): void {
    keys.forEach((k) => this.remove(k));
  }
}

let _instance: CredentialStore | null = null;

export function getCredentialStore(): CredentialStore {
  if (!_instance) {
    _instance = new SessionStorageCredentialStore();
  }
  return _instance;
}

/** Replace the active store — for unit tests only. */
export function setCredentialStore(store: CredentialStore): void {
  _instance = store;
}

/** Reset to the default store — call in afterEach. */
export function resetCredentialStore(): void {
  _instance = null;
}
