import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export interface CatalogSet {
  set_code: string;
  card_count: number;
  priced_count: number;
}

export function useCatalogSets() {
  const [sets, setSets] = useState<CatalogSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<CatalogSet[]>("/api/catalog/sets")
      .then((res) => {
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else if (res.data) {
          setSets(res.data);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return { sets, loading, error };
}
