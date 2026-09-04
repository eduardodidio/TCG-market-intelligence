import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface CatalogStats {
  total_cards: number;
  total_sets: number;
  cards_with_price: number;
  cards_without_price: number;
}

export function useCatalogStats() {
  const [stats, setStats] = useState<CatalogStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<CatalogStats>("/api/catalog/stats")
      .then((res) => {
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else if (res.data) {
          setStats(res.data);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return { stats, loading, error };
}
