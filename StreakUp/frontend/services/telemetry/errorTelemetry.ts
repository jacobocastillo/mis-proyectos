"use client";

import { apiPost, API_ENDPOINTS } from "@/services/api/client";

export interface ClientErrorReport {
  message: string;
  name?: string;
  stack?: string;
  component?: string;
  url?: string;
  userAgent?: string;
  release?: string;
  environment?: string;
}

function getErrorReport(error: unknown, component?: string): ClientErrorReport {
  if (error instanceof Error) {
    return {
      message: error.message || "Unknown client error",
      name: error.name,
      stack: error.stack,
      component,
      url: typeof window !== "undefined" ? window.location.href : undefined,
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : undefined,
      environment: process.env.NODE_ENV,
    };
  }

  return {
    message: typeof error === "string" ? error : "Unknown client error",
    component,
    url: typeof window !== "undefined" ? window.location.href : undefined,
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : undefined,
    environment: process.env.NODE_ENV,
  };
}

export async function reportClientError(error: unknown, component?: string): Promise<void> {
  const report = getErrorReport(error, component);

  try {
    await apiPost(API_ENDPOINTS.telemetry.errors, JSON.stringify(report));
  } catch {
    // Telemetry must never create a secondary user-facing failure.
  }
}
