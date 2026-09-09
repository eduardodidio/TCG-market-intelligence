import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams, Link } from "react-router-dom";
import { fetchCollection, fetchCollectionSummary } from "../api/collection";
import { Card3DTilt } from "../components/Card3DTilt";
import { CardImage } from "../components/CardImage";
import { EmptyState } from "../components/EmptyState";
import { SortSelect, COLLECTION_SORT_OPTIONS } from "../components/SortSelect";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import type { CollectionCard, CollectionSummary } from "../types/api";
import { DEFAULT_PAGE_LIMIT } from "../utils/constants";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

export default function CollectionV2() {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const { getCardName } = useCardName();

  const [searchParams, setSearchParams] = useSearchParams();
  const [sortBy, setSortBy] = useState(searchParams.get("sort") ?? "price");
  const [sortDir, setSortDir] = useState<"asc" | "desc">(
    (searchParams.get("dir") as "asc" | "desc") ?? "desc",
  );
  const [search, setSearch] = useState(searchParams.get("q") ?? "");
  const debouncedSearch = useDebounce(search, 300);

  const [cards, setCards] = useState<CollectionCard[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<CollectionSummary | null>(null);

  const fetchIdRef = useRef(0);

  useEffect(() => {
    document.title = `${t("collection.title")} | TCG Market`;
  }, [t]);

  // Build API params
  const buildParams = useCallback(
    (currentOffset: number): Record<string, string> => {
      const params: Record<string, string> = {
        limit: String(DEFAULT_PAGE_LIMIT),
        offset: String(currentOffset),
      };
      if (debouncedSearch) params.name = debouncedSearch;
      if (sortBy !== "price") {
        params.sort_by = sortBy;
        params.sort_dir = sortDir;
      }
      if (currency !== "BRL") {
        params.currency = currency;
      }
      return params;
    },
    [debouncedSearch, sortBy, sortDir, currency],
  );

  // Load summary
  useEffect(() => {
    fetchCollectionSummary({ currency }).then((res) => {
      if (res.data) setSummary(res.data);
    });
  }, [currency]);

  // Sync URL params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (debouncedSearch) params.q = debouncedSearch;
    if (sortBy !== "price") params.sort = sortBy;
    if (sortDir !== "desc") params.dir = sortDir;
    setSearchParams(params, { replace: true });
  }, [debouncedSearch, sortBy, sortDir, setSearchParams]);

  // Fetch collection cards
  useEffect(() => {
    fetchIdRef.current += 1;
    const currentId = fetchIdRef.current;

    setLoading(true);
    setError(null);
    setOffset(0);
    setCards([]);
    setHasMore(false);

    fetchCollection(buildParams(0))
      .then((res) => {
        if (currentId !== fetchIdRef.current) return;
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else {
          const data = res.data ?? [];
          setCards(data);
          const total = res.meta.total;
          setHasMore(
            total != null ? data.length < total : data.length >= DEFAULT_PAGE_LIMIT,
          );
          setOffset(data.length);
        }
      })
      .catch((err: unknown) => {
        if (currentId !== fetchIdRef.current) return;
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      })
      .finally(() => {
        if (currentId === fetchIdRef.current) setLoading(false);
      });
  }, [debouncedSearch, sortBy, sortDir, currency, buildParams, t]);

  const handleLoadMore = useCallback(() => {
    if (!hasMore || loadingMore) return;
    setLoadingMore(true);

    fetchCollection(buildParams(offset))
      .then((res) => {
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
        } else {
          const data = res.data ?? [];
          setCards((prev) => [...prev, ...data]);
          const newOffset = offset + data.length;
          setOffset(newOffset);
          const total = res.meta.total;
          setHasMore(
            total != null ? newOffset < total : data.length >= DEFAULT_PAGE_LIMIT,
          );
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      })
      .finally(() => setLoadingMore(false));
  }, [hasMore, loadingMore, offset, buildParams, t]);

  const sentinelRef = useInfiniteScroll(handleLoadMore, {
    enabled: hasMore && !loadingMore,
  });

  const handleSortChange = useCallback(
    (newSortBy: string, newSortDir: "asc" | "desc") => {
      setSortBy(newSortBy);
      setSortDir(newSortDir);
    },
    [],
  );

  // Client-side price sorting
  const sortedCards = useMemo(() => {
    if (sortBy !== "price") return cards;
    return [...cards].sort((a, b) => {
      const pa = a.latest_price ?? (sortDir === "asc" ? Infinity : -Infinity);
      const pb = b.latest_price ?? (sortDir === "asc" ? Infinity : -Infinity);
      return sortDir === "asc" ? pa - pb : pb - pa;
    });
  }, [cards, sortBy, sortDir]);

  return (
    <div
      className="font-figtree max-w-7xl mx-auto px-fluid-md py-fluid-md"
      data-testid="page-collection-v2"
    >
      {/* Header */}
      <div className="mb-fluid-md">
        <h1 className="v2-heading text-3xl">{t("collection.title")}</h1>
        {summary && (
          <p className="v2-body mt-2" data-testid="collection-summary">
            {summary.total_unique} {t("collection.uniqueCards").toLowerCase()}
            {" | "}
            {formatCurrency(summary.total_value, currency)}
            {" | "}
            {summary.sets_count} {t("collection.sets").toLowerCase()}
          </p>
        )}
      </div>

      {/* Sticky Filter Bar */}
      <div
        className="sticky top-16 z-40 backdrop-blur-md bg-v2-bg/80 border-b border-v2-border py-3 mb-fluid-md -mx-fluid-md px-fluid-md"
        data-testid="v2-filter-bar"
      >
        {/* Large search input */}
        <input
          type="text"
          placeholder={t("cards.search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-v2-surface border border-v2-border rounded-v2 px-4 py-3 text-white placeholder-v2-muted focus:border-v2-accent focus:ring-1 focus:ring-v2-accent outline-none font-figtree"
          data-testid="v2-search-input"
        />
        {/* Sort row below search */}
        <div className="flex gap-3 mt-3">
          <SortSelect
            options={COLLECTION_SORT_OPTIONS}
            value={`${sortBy}-${sortDir}`}
            onChange={handleSortChange}
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-fluid-md p-4 bg-red-900/30 border border-red-500/30 rounded-v2 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-fluid-md"
          data-testid="v2-skeleton-grid"
        >
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="v2-card overflow-hidden animate-pulse">
              <div className="aspect-[5/7] bg-v2-surface-hover" />
              <div className="p-3 space-y-2">
                <div className="h-4 bg-v2-surface-hover rounded w-3/4" />
                <div className="h-3 bg-v2-surface-hover rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && cards.length === 0 && (
        <EmptyState
          title={
            debouncedSearch
              ? t("collection.noMatchingCards")
              : t("onboarding.collectionEmptyTitle")
          }
          description={
            debouncedSearch ? undefined : t("onboarding.collectionEmptyDesc")
          }
          action={
            debouncedSearch
              ? { label: t("common.clearFilters"), onClick: () => setSearch("") }
              : undefined
          }
        />
      )}

      {/* Card Grid - large hero cards */}
      {!loading && sortedCards.length > 0 && (
        <>
          <div
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-fluid-md"
            data-testid="v2-collection-grid"
          >
            {sortedCards.map((card) => {
              const displayName = getCardName(
                card.name_en,
                card.name_pt,
                t("common.unknownCard"),
              );
              const primaryUrl =
                card.image_url ||
                scryfallImageUrl(card.set_code, card.collector_number);
              const fallbackUrl = card.name_en
                ? scryfallImageByName(card.name_en)
                : null;

              return (
                <Link
                  key={card.id}
                  to={`/collection/${card.id}`}
                  className="group no-underline"
                  data-testid={`v2-card-${card.id}`}
                >
                  <div className="v2-card overflow-hidden">
                    <Card3DTilt foil={card.is_foil}>
                      <div className="aspect-[5/7] bg-gradient-to-br from-v2-surface to-v2-surface-hover overflow-hidden">
                        <CardImage
                          src={primaryUrl}
                          fallbackSrc={fallbackUrl}
                          alt={displayName}
                          className="w-full h-full"
                        />
                      </div>
                    </Card3DTilt>
                    <div className="p-3">
                      <p className="text-white font-medium text-sm truncate">
                        {displayName}
                      </p>
                      <div className="flex justify-between items-center mt-1">
                        <span
                          className="v2-accent text-sm"
                          data-testid="v2-card-price"
                        >
                          {card.latest_price != null
                            ? formatCurrency(card.latest_price, currency)
                            : "\u2014"}
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>

          {/* Infinite scroll sentinel */}
          <div ref={sentinelRef} data-testid="v2-scroll-sentinel" />

          {/* Loading more indicator */}
          {loadingMore && (
            <div
              className="flex justify-center mt-fluid-md"
              data-testid="v2-loading-more"
            >
              <div className="h-6 w-6 border-2 border-v2-accent border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
