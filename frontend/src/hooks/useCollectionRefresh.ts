import { useCallback, useEffect, useRef, useState } from "react";
import { triggerScanAuth, getScanStatusAuth } from "../api/scans";

const POLL_INTERVAL_MS = 3_000;
const COMPLETE_DISPLAY_MS = 2_000;
const ERROR_DISPLAY_MS = 3_000;

export interface RefreshProgress {
  processed: number;
  total: number;
}

export interface UseCollectionRefreshReturn {
  isRefreshing: boolean;
  progress: RefreshProgress | null;
  error: string | null;
  isDone: boolean;
  startRefresh: () => Promise<void>;
  cancelRefresh: () => void;
}

export function useCollectionRefresh(
  onComplete?: () => void,
): UseCollectionRefreshReturn {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [progress, setProgress] = useState<RefreshProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDone, setIsDone] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const doneTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimers = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (doneTimerRef.current) {
      clearTimeout(doneTimerRef.current);
      doneTimerRef.current = null;
    }
    if (errorTimerRef.current) {
      clearTimeout(errorTimerRef.current);
      errorTimerRef.current = null;
    }
  }, []);

  const cancelRefresh = useCallback(() => {
    clearTimers();
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsRefreshing(false);
    setProgress(null);
    setError(null);
    setIsDone(false);
  }, [clearTimers]);

  const startRefresh = useCallback(async () => {
    // Prevent double-starts
    if (isRefreshing) return;

    // Reset state
    setError(null);
    setIsDone(false);
    setIsRefreshing(true);
    setProgress(null);

    const controller = new AbortController();
    abortRef.current = controller;

    // Trigger scan
    const res = await triggerScanAuth({ scan_type: "collection" });

    if (controller.signal.aborted) return;

    if (res.errors.length > 0 || !res.data) {
      const msg = res.errors[0]?.message || "Failed to start scan";
      setError(msg);
      setIsRefreshing(false);
      errorTimerRef.current = setTimeout(() => {
        setError(null);
      }, ERROR_DISPLAY_MS);
      return;
    }

    const scanId = res.data.scan_id;

    // Start polling
    intervalRef.current = setInterval(async () => {
      if (controller.signal.aborted) {
        clearTimers();
        return;
      }

      const statusRes = await getScanStatusAuth(scanId);

      if (controller.signal.aborted) return;

      if (statusRes.errors.length > 0 || !statusRes.data) {
        clearTimers();
        const msg = statusRes.errors[0]?.message || "Failed to get scan status";
        setError(msg);
        setIsRefreshing(false);
        errorTimerRef.current = setTimeout(() => {
          setError(null);
        }, ERROR_DISPLAY_MS);
        return;
      }

      const scan = statusRes.data;
      setProgress({
        processed: scan.cards_processed,
        total: scan.cards_total,
      });

      if (scan.status === "completed") {
        clearTimers();
        setIsRefreshing(false);
        setIsDone(true);
        onComplete?.();
        doneTimerRef.current = setTimeout(() => {
          setIsDone(false);
          setProgress(null);
        }, COMPLETE_DISPLAY_MS);
      } else if (scan.status === "failed") {
        clearTimers();
        setIsRefreshing(false);
        setError(scan.error_summary || "Scan failed");
        errorTimerRef.current = setTimeout(() => {
          setError(null);
          setProgress(null);
        }, ERROR_DISPLAY_MS);
      }
    }, POLL_INTERVAL_MS);
  }, [isRefreshing, clearTimers, onComplete]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers();
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, [clearTimers]);

  return {
    isRefreshing,
    progress,
    error,
    isDone,
    startRefresh,
    cancelRefresh,
  };
}
