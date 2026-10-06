"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { ThemeProvider } from "next-themes";
import { AppErrorBoundary } from "@/components/feedback/AppErrorBoundary";
import { drainSyncQueue, recoverInterruptedSync } from "@/services/sync/syncService";
import { reportClientError } from "@/services/telemetry/errorTelemetry";

interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  useEffect(() => {
    recoverInterruptedSync();

    if (typeof navigator !== "undefined" && navigator.onLine) {
      void drainSyncQueue();
    }

    function handleOnline() {
      void drainSyncQueue();
    }

    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, []);

  useEffect(() => {
    function handleError(event: ErrorEvent) {
      void reportClientError(event.error ?? event.message, "window.error");
    }

    function handleUnhandledRejection(event: PromiseRejectionEvent) {
      void reportClientError(event.reason, "window.unhandledrejection");
    }

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleUnhandledRejection);
    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleUnhandledRejection);
    };
  }, []);

  return (
    <ThemeProvider attribute="class" defaultTheme="theme-fire" themes={['theme-fire', 'theme-ice', 'theme-candy', 'theme-night', 'light', 'dark']} enableSystem={false} disableTransitionOnChange>
      <AppErrorBoundary>{children}</AppErrorBoundary>
    </ThemeProvider>
  );
}
