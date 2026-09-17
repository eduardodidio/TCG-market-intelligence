import { useCallback, useEffect, useRef, useState } from "react";
import type { PriceRequestStatus } from "../api/cards";
import { fetchPriceRequestStatus } from "../api/cards";

export interface UsePriceRequestPollingOptions {
  cardId: number;
  enabled: boolean;
  onCompleted?: (price: number | null) => void;
  onFailed?: () => void;
  intervalMs?: number;
  maxDurationMs?: number;
}

export interface UsePriceRequestPollingResult {
  status: PriceRequestStatus["status"];
  isPolling: boolean;
  resultPrice: number | null;
}

const DEFAULT_INTERVAL_MS = 5_000;
const DEFAULT_MAX_DURATION_MS = 60_000;

export function usePriceRequestPolling({
  cardId,
  enabled,
  onCompleted,
  onFailed,
  intervalMs = DEFAULT_INTERVAL_MS,
  maxDurationMs = DEFAULT_MAX_DURATION_MS,
}: UsePriceRequestPollingOptions): UsePriceRequestPollingResult {
  const [status, setStatus] = useState<PriceRequestStatus["status"]>("none");
  const [isPolling, setIsPolling] = useState(false);
  const [resultPrice, setResultPrice] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const onCompletedRef = useRef(onCompleted);
  const onFailedRef = useRef(onFailed);

  // Keep callbacks fresh without restarting polling
  onCompletedRef.current = onCompleted;
  onFailedRef.current = onFailed;

  const stopPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const poll = useCallback(async () => {
    // Check timeout
    const elapsed = Date.now() - startTimeRef.current;
    if (elapsed >= maxDurationMs) {
      stopPolling();
      return;
    }

    try {
      const res = await fetchPriceRequestStatus(cardId);
      if (!res.data) return;

      const newStatus = res.data.status;
      setStatus(newStatus);

      if (newStatus === "completed") {
        const price = res.data.result_price ?? null;
        setResultPrice(price);
        stopPolling();
        onCompletedRef.current?.(price);
      } else if (newStatus === "failed") {
        stopPolling();
        onFailedRef.current?.();
      } else if (newStatus === "none") {
        // No request found — stop immediately
        stopPolling();
      }
    } catch {
      // Network error during poll — continue polling
    }
  }, [cardId, maxDurationMs, stopPolling]);

  useEffect(() => {
    if (enabled) {
      setStatus("pending");
      setResultPrice(null);
      setIsPolling(true);
      startTimeRef.current = Date.now();

      // Do an initial poll immediately
      poll();

      intervalRef.current = setInterval(poll, intervalMs);
    } else {
      stopPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, cardId, intervalMs, poll, stopPolling]);

  return { status, isPolling, resultPrice };
}
