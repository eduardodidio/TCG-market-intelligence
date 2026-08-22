import { useCallback, useEffect, useRef, useState } from "react";
import { useCurrency } from "./useCurrency";
import { fetchTickerData } from "../api/trending";
import type { TickerItemData } from "../types/api";

const REFRESH_INTERVAL_MS = 300_000; // 5 minutes

export function useTickerData(): {
  items: TickerItemData[];
  loading: boolean;
} {
  const { currency } = useCurrency();
  const [items, setItems] = useState<TickerItemData[]>([]);
  const [loading, setLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(
    async (isInitial: boolean) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      if (isInitial) setLoading(true);

      const data = await fetchTickerData(currency, controller.signal);
      if (!controller.signal.aborted) {
        setItems(data);
        if (isInitial) setLoading(false);
      }
    },
    [currency],
  );

  useEffect(() => {
    fetchData(true);

    intervalRef.current = setInterval(() => {
      fetchData(false);
    }, REFRESH_INTERVAL_MS);

    return () => {
      abortRef.current?.abort();
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData]);

  return { items, loading };
}
