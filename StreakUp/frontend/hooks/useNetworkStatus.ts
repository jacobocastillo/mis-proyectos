/**
 * useNetworkStatus
 *
 * Reactively tracks the device's online/offline state using the browser's
 * navigator.onLine flag and the window online/offline events.
 *
 * Returns:
 *   isOnline  - true when the device has network connectivity
 *   isOffline - convenience inverse of isOnline
 *
 * Usage:
 *   const { isOnline, isOffline } = useNetworkStatus();
 *
 * Notes:
 *   - navigator.onLine can return true even when there is no actual internet
 *     access (e.g. connected to a LAN without a gateway).  Treat this as a
 *     "best-effort" signal, not a guarantee of reachability.
 *   - Safe for SSR: defaults to true (online) on the server where
 *     navigator is undefined.
 */

"use client";

import { useState, useEffect } from "react";

export interface NetworkStatus {
  isOnline: boolean;
  isOffline: boolean;
}

export function useNetworkStatus(): NetworkStatus {
  const [isOnline, setIsOnline] = useState<boolean>(() => {
    if (typeof navigator === "undefined") {
      return true; // SSR-safe default
    }
    return navigator.onLine;
  });

  useEffect(() => {
    function handleOnline() {
      setIsOnline(true);
    }

    function handleOffline() {
      setIsOnline(false);
    }

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Sync with the real state in case it changed before the listeners attached.
    setIsOnline(navigator.onLine);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return { isOnline, isOffline: !isOnline };
}
