import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { fetchCards } from "../api/cards";
import { fetchSets } from "../api/sets";
import { CardTile } from "../components/CardTile";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { FilterChips } from "../components/FilterChips";
import { SearchBar } from "../components/SearchBar";
import { SkeletonCard } from "../components/Skeleton";
import { SortSelect, EXPLORE_SORT_OPTIONS } from "../components/SortSelect";
import { useCurrency } from "../hooks/useCurrency";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import type { CardSummary, SetSummary } from "../types/api";
import { DEFAULT_PAGE_LIMIT } from "../utils/constants";

export function Cards() {
  const { t } = useTranslation();

  useEffect(() => {
    document.title = `${t("cards.title")} | TCG Market`;
  }, [t]);

  const { currency } = useCurrency();
  const [searchParams, setSearchParams] = useSearchParams();

  const [searchTerm, setSearchTerm] = useState(
    searchParams.get("name") ?? "",
  );
  const [selectedSet, setSelectedSet] = useState<string | null>(
    searchParams.get("set") ?? null,
  );
  const [sortBy, setSortBy] = useState(searchParams.get("sort") ?? "name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">((searchParams.get("dir") as "asc" | "desc") ?? "asc");
  const [cards, setCards] = useState<CardSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sets, setSets] = useState<SetSummary[]>([]);

  const debouncedSearch = useDebounce(searchTerm, 300);
  const fetchIdRef = useRef(0);

  // Load sets on mount
  useEffect(() => {
    fetchSets()
      .then((res) => {
        if (res.data) setSets(res.data);
      })
      .catch(() => {
        setError(t("cards.setsLoadError"));
      });
  }, [t]);

  // Sync search params to URL
  useEffect(() => {
    const params: Record<string, string> = {};
    if (debouncedSearch) params.name = debouncedSearch;
    if (selectedSet) params.set = selectedSet;
    if (sortBy !== "name") params.sort = sortBy;
    if (sortDir !== "asc") params.dir = sortDir;
    setSearchParams(params, { replace: true });
  }, [debouncedSearch, selectedSet, sortBy, sortDir, setSearchParams]);

  // Fetch cards when filters change
  useEffect(() => {
    fetchIdRef.current += 1;
    const currentFetchId = fetchIdRef.current;

    setLoading(true);
    setError(null);
    setCursor(null);
    setCards([]);

    const params: Record<string, string> = {
      limit: String(DEFAULT_PAGE_LIMIT),
      currency,
    };
    if (debouncedSearch) params.name = debouncedSearch;
    if (selectedSet) params.set = selectedSet;
    if (sortBy !== "price") {
      params.sort_by = sortBy;
      params.sort_dir = sortDir;
    }

    fetchCards(params)
      .then((res) => {
        if (currentFetchId !== fetchIdRef.current) return;
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else {
          setCards(res.data ?? []);
          setCursor(res.meta.cursor);
        }
      })
      .catch((err: unknown) => {
        if (currentFetchId !== fetchIdRef.current) return;
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      })
      .finally(() => {
        if (currentFetchId === fetchIdRef.current) {
          setLoading(false);
        }
      });
  }, [debouncedSearch, selectedSet, sortBy, sortDir, currency]);

  // Load more handler
  const handleLoadMore = useCallback(() => {
    if (!cursor || loadingMore) return;

    setLoadingMore(true);
    const params: Record<string, string> = {
      limit: String(DEFAULT_PAGE_LIMIT),
      cursor,
      currency,
    };
    if (debouncedSearch) params.name = debouncedSearch;
    if (selectedSet) params.set = selectedSet;
    if (sortBy !== "price") {
      params.sort_by = sortBy;
      params.sort_dir = sortDir;
    }

    fetchCards(params)
      .then((res) => {
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else {
          setCards((prev) => [...prev, ...(res.data ?? [])]);
          setCursor(res.meta.cursor);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      })
      .finally(() => {
        setLoadingMore(false);
      });
  }, [cursor, loadingMore, debouncedSearch, selectedSet, sortBy, sortDir, currency]);

  const setOptions = sets.map((s) => ({
    label: s.set_code,
    value: s.set_code,
  }));

  const sentinelRef = useInfiniteScroll(handleLoadMore, {
    enabled: !!cursor && !loadingMore,
  });

  const handleClearFilters = useCallback(() => {
    setSearchTerm("");
    setSelectedSet(null);
  }, []);

  const handleSortChange = useCallback((newSortBy: string, newSortDir: "asc" | "desc") => {
    setSortBy(newSortBy);
    setSortDir(newSortDir);
  }, []);

  return (
    <div data-testid="page-cards">
      <h2 className="text-2xl font-bold text-white mb-6">{t("cards.title")}</h2>

      {/* Search and filters */}
      <div className="space-y-4 mb-6">
        <div className="flex gap-3 items-center">
          <div className="flex-1">
            <SearchBar value={searchTerm} onChange={setSearchTerm} />
          </div>
          <SortSelect
            options={EXPLORE_SORT_OPTIONS}
            value={`${sortBy}-${sortDir}`}
            onChange={handleSortChange}
          />
        </div>

        {setOptions.length > 0 && (
          <FilterChips
            options={setOptions}
            selected={selectedSet}
            onSelect={setSelectedSet}
          />
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6">
          <ErrorBanner message={error} variant="inline" />
        </div>
      )}

      {/* Loading state — skeleton cards */}
      {loading && (
        <div
          className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-4"
          data-testid="skeleton-grid"
        >
          {Array.from({ length: 12 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && cards.length === 0 && (
        <EmptyState
          message={
            debouncedSearch || selectedSet
              ? t("cards.noCardsFiltered")
              : t("cards.noCardsEmpty")
          }
          action={
            debouncedSearch || selectedSet
              ? { label: t("common.clearFilters"), onClick: handleClearFilters }
              : undefined
          }
        />
      )}

      {/* Cards grid */}
      {!loading && cards.length > 0 && (
        <>
          <div
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-4"
            data-testid="cards-grid"
          >
            {cards.map((card) => (
              <CardTile key={card.id} card={card} />
            ))}
          </div>

          <div ref={sentinelRef} data-testid="scroll-sentinel" />
          {loadingMore && (
            <div className="flex justify-center mt-4" data-testid="loading-more">
              <div className="h-6 w-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
