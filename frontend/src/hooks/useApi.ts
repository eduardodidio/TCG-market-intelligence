import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse } from "../types/api";

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  setData: (data: T | null) => void;
}

/**
 * Generic data-fetching hook with AbortController cleanup.
 * Extracts data from the API envelope and handles loading/error states.
 */
export function useApi<T>(
  fetcher: (signal: AbortSignal) => Promise<ApiResponse<T>>,
  deps: unknown[] = [],
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetchCountRef = useRef(0);

  const execute = useCallback(() => {
    const controller = new AbortController();
    fetchCountRef.current += 1;
    const currentFetch = fetchCountRef.current;

    setLoading(true);
    setError(null);

    fetcher(controller.signal)
      .then((response) => {
        // Ignore stale responses
        if (currentFetch !== fetchCountRef.current) return;

        if (response.errors.length > 0) {
          setError(response.errors.map((e) => e.message).join("; "));
          setData(null);
        } else {
          setData(response.data);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (currentFetch !== fetchCountRef.current) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Unknown error");
        setData(null);
      })
      .finally(() => {
        if (currentFetch === fetchCountRef.current) {
          setLoading(false);
        }
      });

    return controller;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    const controller = execute();
    return () => controller.abort();
  }, [execute]);

  const refetch = useCallback(() => {
    execute();
  }, [execute]);

  return { data, loading, error, refetch, setData };
}
