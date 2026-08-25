import { useCallback, useEffect, useRef, useState } from "react";
import { triggerScanAuth } from "../api/scans";
import type { ScanStreamEvent } from "./useScanStream";
import { useScanStream } from "./useScanStream";

const COMPLETE_DISPLAY_MS = 2_000;
const ERROR_DISPLAY_MS = 3_000;

export interface RefreshProgress {
  processed: number;
  total: number;
}

export interface LastScannedCard {
  name: string;
  externalId?: string;
  priceFound: boolean;
  price?: number;
}

export interface UseCollectionRefreshReturn {
  isRefreshing: boolean;
  progress: RefreshProgress | null;
  error: string | null;
  isDone: boolean;
  lastScannedCard: LastScannedCard | null;
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
  const [lastScannedCard, setLastScannedCard] = useState<LastScannedCard | null>(null);
  const [scanId, setScanId] = useState<number | null>(null);

  const doneTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  // Get JWT token from localStorage
  const token = typeof localStorage !== "undefined"
    ? localStorage.getItem("tcg_access_token") || ""
    : "";

  const clearTimers = useCallback(() => {
    if (doneTimerRef.current) {
      clearTimeout(doneTimerRef.current);
      doneTimerRef.current = null;
    }
    if (errorTimerRef.current) {
      clearTimeout(errorTimerRef.current);
      errorTimerRef.current = null;
    }
  }, []);

  const handleEvent = useCallback((event: ScanStreamEvent) => {
    setProgress({
      processed: event.cards_processed,
      total: event.cards_total,
    });
    if (event.event_type === "card_scanned" && event.card_name) {
      setLastScannedCard({
        name: event.card_name,
        externalId: event.external_id,
        priceFound: event.price_found ?? false,
        price: event.price,
      });
    }
  }, []);

  const handleComplete = useCallback((event: ScanStreamEvent) => {
    setProgress({
      processed: event.cards_processed,
      total: event.cards_total,
    });
    setIsRefreshing(false);
    setIsDone(true);
    setScanId(null);
    localStorage.removeItem("tcg_active_scan");
    onCompleteRef.current?.();
    doneTimerRef.current = setTimeout(() => {
      setIsDone(false);
      setProgress(null);
      setLastScannedCard(null);
    }, COMPLETE_DISPLAY_MS);
  }, []);

  const handleStreamError = useCallback((msg: string) => {
    clearTimers();
    setIsRefreshing(false);
    setScanId(null);
    localStorage.removeItem("tcg_active_scan");
    setError(msg);
    errorTimerRef.current = setTimeout(() => {
      setError(null);
      setProgress(null);
      setLastScannedCard(null);
    }, ERROR_DISPLAY_MS);
  }, [clearTimers]);

  const { disconnect } = useScanStream({
    scanId,
    token,
    onEvent: handleEvent,
    onComplete: handleComplete,
    onError: handleStreamError,
    fallbackToPolling: true,
  });

  const cancelRefresh = useCallback(() => {
    clearTimers();
    disconnect();
    setScanId(null);
    setIsRefreshing(false);
    localStorage.removeItem("tcg_active_scan");
    setProgress(null);
    setError(null);
    setIsDone(false);
    setLastScannedCard(null);
  }, [clearTimers, disconnect]);

  const startRefresh = useCallback(async () => {
    if (isRefreshing) return;

    setError(null);
    setIsDone(false);
    setIsRefreshing(true);
    setProgress(null);
    setLastScannedCard(null);

    const res = await triggerScanAuth({ scan_type: "collection", provider: "liga" });

    if (res.errors.length > 0 || !res.data) {
      const msg = res.errors[0]?.message || "Failed to start scan";
      setError(msg);
      setIsRefreshing(false);
      errorTimerRef.current = setTimeout(() => {
        setError(null);
      }, ERROR_DISPLAY_MS);
      return;
    }

    // Set scanId to trigger SSE connection via useScanStream
    setScanId(res.data.scan_id);
    localStorage.setItem("tcg_active_scan", JSON.stringify({ scanId: res.data.scan_id }));
  }, [isRefreshing]);

  // Resume active scan from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("tcg_active_scan");
    if (stored) {
      try {
        const { scanId: storedScanId } = JSON.parse(stored);
        if (storedScanId && !isRefreshing) {
          setIsRefreshing(true);
          setScanId(storedScanId);
        }
      } catch {
        localStorage.removeItem("tcg_active_scan");
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers();
      disconnect();
    };
  }, [clearTimers, disconnect]);

  return {
    isRefreshing,
    progress,
    error,
    isDone,
    lastScannedCard,
    startRefresh,
    cancelRefresh,
  };
}
