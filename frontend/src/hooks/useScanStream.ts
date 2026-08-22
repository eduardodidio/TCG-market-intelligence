import { useCallback, useEffect, useRef, useState } from "react";
import { getScanStatusAuth } from "../api/scans";
import { API_BASE_URL } from "../utils/constants";

export interface ScanStreamEvent {
  event_type: "scan_started" | "card_scanned" | "scan_complete";
  scan_id: number;
  timestamp: string;
  external_id?: string;
  card_name?: string;
  price_found?: boolean;
  price?: number;
  currency?: string;
  error?: string;
  cards_processed: number;
  cards_total: number;
  cards_failed: number;
  observations_saved: number;
}

export interface UseScanStreamOptions {
  scanId: number | null;
  token: string;
  onEvent?: (event: ScanStreamEvent) => void;
  onComplete?: (event: ScanStreamEvent) => void;
  onError?: (error: string) => void;
  fallbackToPolling?: boolean;
}

export interface UseScanStreamReturn {
  isConnected: boolean;
  lastEvent: ScanStreamEvent | null;
  progress: { processed: number; total: number } | null;
  error: string | null;
  disconnect: () => void;
}

const POLL_INTERVAL_MS = 3_000;

export function useScanStream({
  scanId,
  token,
  onEvent,
  onComplete,
  onError,
  fallbackToPolling = true,
}: UseScanStreamOptions): UseScanStreamReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<ScanStreamEvent | null>(null);
  const [progress, setProgress] = useState<{ processed: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const callbacksRef = useRef({ onEvent, onComplete, onError });
  callbacksRef.current = { onEvent, onComplete, onError };

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    stopPolling();
    setIsConnected(false);
  }, [stopPolling]);

  const startPollingFallback = useCallback(
    (id: number) => {
      if (pollingRef.current) return;
      pollingRef.current = setInterval(async () => {
        const res = await getScanStatusAuth(id);
        if (res.errors.length > 0 || !res.data) {
          stopPolling();
          const msg = res.errors[0]?.message || "Failed to get scan status";
          setError(msg);
          callbacksRef.current.onError?.(msg);
          return;
        }
        const scan = res.data;
        const evt: ScanStreamEvent = {
          event_type:
            scan.status === "completed" || scan.status === "failed"
              ? "scan_complete"
              : "card_scanned",
          scan_id: id,
          timestamp: new Date().toISOString(),
          cards_processed: scan.cards_processed,
          cards_total: scan.cards_total,
          cards_failed: scan.cards_failed,
          observations_saved: scan.observations_saved,
          error: scan.error_summary || undefined,
        };
        setLastEvent(evt);
        setProgress({ processed: scan.cards_processed, total: scan.cards_total });
        callbacksRef.current.onEvent?.(evt);

        if (scan.status === "completed" || scan.status === "failed") {
          stopPolling();
          setIsConnected(false);
          callbacksRef.current.onComplete?.(evt);
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling],
  );

  useEffect(() => {
    if (scanId === null || !token) {
      return;
    }

    const baseUrl = API_BASE_URL || window.location.origin;
    const url = `${baseUrl}/api/v1/scans/${scanId}/stream?token=${encodeURIComponent(token)}`;

    let es: EventSource;
    try {
      es = new EventSource(url);
    } catch {
      if (fallbackToPolling) {
        startPollingFallback(scanId);
        setIsConnected(true);
      }
      return;
    }

    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    const handleEvent = (e: MessageEvent) => {
      try {
        const data: ScanStreamEvent = JSON.parse(e.data);
        setLastEvent(data);
        setProgress({ processed: data.cards_processed, total: data.cards_total });
        callbacksRef.current.onEvent?.(data);

        if (data.event_type === "scan_complete") {
          callbacksRef.current.onComplete?.(data);
          es.close();
          eventSourceRef.current = null;
          setIsConnected(false);
        }
      } catch {
        // Ignore parse errors (e.g. keepalive comments)
      }
    };

    es.addEventListener("scan_started", handleEvent);
    es.addEventListener("card_scanned", handleEvent);
    es.addEventListener("scan_complete", handleEvent);

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;

      if (fallbackToPolling) {
        setError(null);
        startPollingFallback(scanId);
      } else {
        const msg = "SSE connection failed";
        setError(msg);
        setIsConnected(false);
        callbacksRef.current.onError?.(msg);
      }
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
      stopPolling();
      setIsConnected(false);
    };
  }, [scanId, token, fallbackToPolling, startPollingFallback, stopPolling]);

  return {
    isConnected,
    lastEvent,
    progress,
    error,
    disconnect,
  };
}
