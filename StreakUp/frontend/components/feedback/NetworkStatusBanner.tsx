"use client";

/**
 * NetworkStatusBanner
 *
 * Renders a fixed, accessible banner at the top of the screen when the device
 * goes offline, and a brief "back online" confirmation when connectivity is
 * restored. The banner is invisible when the device is online and no recent
 * reconnection happened.
 *
 * Integrate once in the root dashboard layout so every page is covered.
 */

import { useEffect, useState } from "react";
import { useNetworkStatus } from "@/hooks/useNetworkStatus";
import { getSession } from "@/services/auth/authService";
import { getPendingOpsCount } from "@/services/sync/syncQueue";
import { WifiOff, Wifi } from "lucide-react";

const RECONNECTED_BANNER_DURATION_MS = 3_000;

export function NetworkStatusBanner() {
  const { isOffline } = useNetworkStatus();
  const [justReconnected, setJustReconnected] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    if (isOffline) {
      const session = getSession();
      const userId = Number(session?.user.id ?? 0);
      setPendingCount(userId > 0 ? getPendingOpsCount(userId) : 0);
    } else {
      setPendingCount(0);
    }
  }, [isOffline]);

  // When the device goes back online, briefly show the "reconnected" banner.
  useEffect(() => {
    if (!isOffline) {
      // Don't flash the banner on first render when already online.
      setJustReconnected((prev) => {
        // prev is only true when we were previously offline, so this avoids
        // the false-positive on mount.
        if (prev === false) return false;
        return true;
      });

      const timer = setTimeout(() => {
        setJustReconnected(false);
      }, RECONNECTED_BANNER_DURATION_MS);

      return () => clearTimeout(timer);
    } else {
      // Going offline: mark that a reconnection event should be shown later.
      setJustReconnected(true);
    }
  }, [isOffline]);

  if (!isOffline && !justReconnected) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed top-0 inset-x-0 z-50 flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold transition-all duration-300 ${
        isOffline
          ? "bg-red-600 text-white"
          : "bg-green-600 text-white"
      }`}
    >
      {isOffline ? (
        <>
          <WifiOff className="size-4 shrink-0" aria-hidden="true" />
          <span>
            Sin conexión
            {pendingCount > 0 ? ` — ${pendingCount} cambio${pendingCount === 1 ? "" : "s"} pendiente${pendingCount === 1 ? "" : "s"}` : " — algunas funciones no están disponibles"}
          </span>
        </>
      ) : (
        <>
          <Wifi className="size-4 shrink-0" aria-hidden="true" />
          <span>Conexión restaurada</span>
        </>
      )}
    </div>
  );
}
