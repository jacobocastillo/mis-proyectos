"use client";

import type { ErrorInfo, ReactNode } from "react";
import { Component } from "react";
import { AlertTriangle } from "lucide-react";

import { reportClientError } from "@/services/telemetry/errorTelemetry";

interface AppErrorBoundaryProps {
  children: ReactNode;
}

interface AppErrorBoundaryState {
  hasError: boolean;
}

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    void reportClientError(error, errorInfo.componentStack ?? "react-boundary");
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex h-full min-h-[100dvh] items-center justify-center px-6 text-center text-white"
          role="alert"
        >
          <div className="space-y-4">
            <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-red-500/20 text-red-200">
              <AlertTriangle className="size-6" aria-hidden="true" />
            </div>
            <div className="space-y-2">
              <h1 className="text-lg font-bold">No se pudo cargar StreakUp</h1>
              <p className="text-sm text-white/72">
                Reinicia la app e inténtalo de nuevo.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
