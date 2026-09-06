import { useCallback, useEffect, useRef, useState } from "react";
import { fetchPriceTrends, type PriceTrendEntry } from "../api/cards";

/**
 * Batch-fetches price trends for a set of card IDs.
 * Debounces requests and caches results to avoid re-fetching.
 */
export function usePriceTrends(cardIds: number[]) {
  const [trends, setTrends] = useState<Record<string, PriceTrendEntry>>({});
  const [loading, setLoading] = useState(false);
  const cacheRef = useRef<Record<string, PriceTrendEntry>>({});
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchTrends = useCallback(async (ids: number[]) => {
    // Filter out already-cached IDs
    const uncached = ids.filter((id) => !(String(id) in cacheRef.current));
    if (uncached.length === 0) {
      // All cached, just update state from cache
      const result: Record<string, PriceTrendEntry> = {};
      for (const id of ids) {
        const entry = cacheRef.current[String(id)];
        if (entry) result[String(id)] = entry;
      }
      setTrends((prev) => ({ ...prev, ...result }));
      return;
    }

    setLoading(true);
    try {
      const res = await fetchPriceTrends(uncached);
      if (res.data) {
        const newTrends = res.data.trends;
        // Update cache
        Object.assign(cacheRef.current, newTrends);
        // Mark IDs with no data in cache too (empty entry)
        for (const id of uncached) {
          if (!(String(id) in cacheRef.current)) {
            cacheRef.current[String(id)] = { prices: [], change_pct: null };
          }
        }
        setTrends((prev) => ({ ...prev, ...newTrends }));
      }
    } catch {
      // Silently fail - sparklines are non-critical
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (cardIds.length === 0) return;

    // Debounce 300ms to avoid rapid calls during scroll
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      // Batch in chunks of 50
      for (let i = 0; i < cardIds.length; i += 50) {
        const chunk = cardIds.slice(i, i + 50);
        fetchTrends(chunk);
      }
    }, 300);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [cardIds.join(","), fetchTrends]);

  return { trends, loading };
}
