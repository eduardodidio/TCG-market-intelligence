import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "../api/client";
import { useDebounce } from "./useDebounce";

export interface CatalogCard {
  id: number;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  rarity: string | null;
  color_identity: string | null;
  mana_cost: string | null;
  type_line: string | null;
  image_uri: string | null;
  liga_price: number | null;
  liga_price_date: string | null;
}

export interface CatalogCardsResponse {
  items: CatalogCard[];
  total: number;
  limit: number;
  offset: number;
}

export interface CatalogFilters {
  name: string;
  set_code: string;
  rarity: string;
  color: string;
  has_price: string;
  min_price: string;
  max_price: string;
  sort_by: string;
  sort_dir: string;
}

const DEFAULT_LIMIT = 50;

export function useCatalogCards(filters: CatalogFilters) {
  const [data, setData] = useState<CatalogCardsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const debouncedName = useDebounce(filters.name, 300);
  const fetchIdRef = useRef(0);

  const buildParams = useCallback(
    (offset = 0): Record<string, string> => {
      const params: Record<string, string> = {
        limit: String(DEFAULT_LIMIT),
        offset: String(offset),
      };
      if (debouncedName) params.name = debouncedName;
      if (filters.set_code) params.set_code = filters.set_code;
      if (filters.rarity) params.rarity = filters.rarity;
      if (filters.color) params.color = filters.color;
      if (filters.has_price) params.has_price = filters.has_price;
      if (filters.min_price) params.min_price = filters.min_price;
      if (filters.max_price) params.max_price = filters.max_price;
      if (filters.sort_by) params.sort_by = filters.sort_by;
      if (filters.sort_dir) params.sort_dir = filters.sort_dir;
      return params;
    },
    [
      debouncedName,
      filters.set_code,
      filters.rarity,
      filters.color,
      filters.has_price,
      filters.min_price,
      filters.max_price,
      filters.sort_by,
      filters.sort_dir,
    ],
  );

  // Fetch cards when filters change
  useEffect(() => {
    fetchIdRef.current += 1;
    const currentFetchId = fetchIdRef.current;

    setLoading(true);
    setError(null);
    setData(null);

    const params = buildParams(0);

    apiGet<CatalogCardsResponse>("/api/catalog/cards", params)
      .then((res) => {
        if (currentFetchId !== fetchIdRef.current) return;
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else if (res.data) {
          setData(res.data);
        }
      })
      .catch((err: unknown) => {
        if (currentFetchId !== fetchIdRef.current) return;
        setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        if (currentFetchId === fetchIdRef.current) {
          setLoading(false);
        }
      });
  }, [buildParams]);

  // Load more handler
  const loadMore = useCallback(() => {
    if (!data || loadingMore) return;
    const nextOffset = data.offset + data.limit;
    if (nextOffset >= data.total) return;

    setLoadingMore(true);

    const params = buildParams(nextOffset);

    apiGet<CatalogCardsResponse>("/api/catalog/cards", params)
      .then((res) => {
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else if (res.data) {
          setData((prev) =>
            prev
              ? {
                  ...res.data!,
                  items: [...prev.items, ...res.data!.items],
                }
              : res.data,
          );
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        setLoadingMore(false);
      });
  }, [data, loadingMore, buildParams]);

  const hasMore = data ? data.offset + data.limit < data.total : false;

  return {
    cards: data?.items ?? [],
    total: data?.total ?? 0,
    loading,
    loadingMore,
    error,
    hasMore,
    loadMore,
  };
}
