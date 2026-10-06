/**
 * useAsyncData
 *
 * Generic hook that manages the lifecycle of an async data-fetch:
 *   - loading  → shows a spinner while the request is in-flight
 *   - data     → holds the successful result
 *   - error    → holds a human-readable error message if the request failed
 *   - refresh  → lets any component trigger a manual retry
 *
 * Usage:
 *   const { data, loading, error, refresh } = useAsyncData(fetchStatsSummary);
 */

"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export interface AsyncDataState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  /**
   * Optional initial value shown before the first successful fetch.
   * Useful when a "skeleton" of empty data is preferable to null.
   */
  initialData?: T,
): AsyncDataState<T> {
  const [data, setData] = useState<T | null>(initialData ?? null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Keep a stable reference to the fetcher so callers can pass inline arrows.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  // Increment this counter each time "refresh" is called so the useEffect re-runs.
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => {
    setTick((n) => n + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    fetcherRef
      .current()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message =
            err instanceof Error && err.message.trim()
              ? err.message
              : "No se pudieron cargar los datos. Inténtalo de nuevo.";
          setError(message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick]);

  return { data, loading, error, refresh };
}
