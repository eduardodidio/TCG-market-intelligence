import { useCallback, useEffect, useRef, useState } from "react";
import { fetchScans, fetchScanDetail, triggerScan } from "../api/scans";
import type { ScanListResponse, ScanRequest, ScanRun, ScanTriggerResponse } from "../types/api";

// ---------------------------------------------------------------------------
// useScans — fetches list of scan runs
// ---------------------------------------------------------------------------

interface UseScansResult {
  scans: ScanRun[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useScans(params?: {
  scan_type?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): UseScansResult {
  const [data, setData] = useState<ScanListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetchCountRef = useRef(0);

  const execute = useCallback(() => {
    fetchCountRef.current += 1;
    const currentFetch = fetchCountRef.current;

    setLoading(true);
    setError(null);

    const queryParams: Record<string, string> = {};
    if (params?.scan_type) queryParams.scan_type = params.scan_type;
    if (params?.status) queryParams.status = params.status;
    if (params?.limit != null) queryParams.limit = String(params.limit);
    if (params?.offset != null) queryParams.offset = String(params.offset);

    fetchScans(queryParams)
      .then((response) => {
        if (currentFetch !== fetchCountRef.current) return;
        setData(response);
        setError(null);
      })
      .catch((err: unknown) => {
        if (currentFetch !== fetchCountRef.current) return;
        setError(err instanceof Error ? err.message : "Unknown error");
        setData(null);
      })
      .finally(() => {
        if (currentFetch === fetchCountRef.current) {
          setLoading(false);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params?.scan_type, params?.status, params?.limit, params?.offset]);

  useEffect(() => {
    execute();
  }, [execute]);

  const refetch = useCallback(() => {
    execute();
  }, [execute]);

  return {
    scans: data?.scans ?? [],
    total: data?.total ?? 0,
    loading,
    error,
    refetch,
  };
}

// ---------------------------------------------------------------------------
// useScanDetail — fetches a single scan run
// ---------------------------------------------------------------------------

interface UseScanDetailResult {
  scan: ScanRun | null;
  loading: boolean;
  error: string | null;
}

export function useScanDetail(id: number | null): UseScanDetailResult {
  const [scan, setScan] = useState<ScanRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchCountRef = useRef(0);

  useEffect(() => {
    if (id == null) {
      setScan(null);
      setLoading(false);
      setError(null);
      return;
    }

    fetchCountRef.current += 1;
    const currentFetch = fetchCountRef.current;

    setLoading(true);
    setError(null);

    fetchScanDetail(id)
      .then((response) => {
        if (currentFetch !== fetchCountRef.current) return;
        setScan(response);
      })
      .catch((err: unknown) => {
        if (currentFetch !== fetchCountRef.current) return;
        setError(err instanceof Error ? err.message : "Unknown error");
        setScan(null);
      })
      .finally(() => {
        if (currentFetch === fetchCountRef.current) {
          setLoading(false);
        }
      });
  }, [id]);

  return { scan, loading, error };
}

// ---------------------------------------------------------------------------
// useTriggerScan — POST to start a new scan
// ---------------------------------------------------------------------------

interface UseTriggerScanResult {
  trigger: (body: ScanRequest) => Promise<ScanTriggerResponse>;
  loading: boolean;
  error: string | null;
}

export function useTriggerScan(): UseTriggerScanResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trigger = useCallback(async (body: ScanRequest): Promise<ScanTriggerResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await triggerScan(body);
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { trigger, loading, error };
}
