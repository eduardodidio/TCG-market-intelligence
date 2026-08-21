import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { fetchCollection, fetchCollectionSummary, fetchCollectionSets } from "../api/collection";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { GridSizeToggle } from "../components/GridSizeToggle";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
import { KpiCard } from "../components/KpiCard";
import { SearchBar } from "../components/SearchBar";
import { SetIconFilter } from "../components/SetIconFilter";
import { SkeletonCard } from "../components/Skeleton";
import { SortSelect, COLLECTION_SORT_OPTIONS } from "../components/SortSelect";
import { useDebounce } from "../hooks/useDebounce";
import { useGridSize } from "../hooks/useGridSize";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import type { CollectionCard, CollectionSummary } from "../types/api";
import { DEFAULT_PAGE_LIMIT, GRID_SIZE_CONFIG } from "../utils/constants";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

const RARITY_COLORS: Record<string, string> = {
  M: "text-amber-400",
  R: "text-yellow-500",
  U: "text-tcg-muted",
  C: "text-tcg-dimmed",
};

const RARITY_LABEL_KEYS: Record<string, string> = {
  M: "rarity.mythic",
  R: "rarity.rare",
  U: "rarity.uncommon",
  C: "rarity.common",
};

function CollectionCardTile({ card, compact = false, currencyOverride }: { card: CollectionCard; compact?: boolean; currencyOverride?: string }) {
  const { t } = useTranslation();
  const displayName = card.name_en || card.name_pt || t("common.unknownCard");
  const [imgError, setImgError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);

  // Primary image: backend-provided URL (Scryfall by set/number)
  // Fallback: Scryfall by exact card name
  const primaryUrl = card.image_url || scryfallImageUrl(card.set_code, card.collector_number);
  const fallbackUrl = card.name_en ? scryfallImageByName(card.name_en) : null;
  const currentUrl = imgError && fallbackUrl ? fallbackUrl : primaryUrl;
  const showImage = !(imgError && (fallbackError || !fallbackUrl));

  const inner = (
    <div
      className="group block bg-tcg-card rounded-tcg-lg overflow-hidden
        border border-tcg-border hover:border-tcg-secondary/50
        transition-all duration-200 hover:scale-[1.02] hover:shadow-tcg-glow-cyan relative cursor-pointer"
      data-testid={`collection-card-${card.id}`}
    >
      {/* Quantity badge */}
      {card.quantity > 1 && (
        <span className="absolute top-2 right-2 z-10 bg-tcg-primary text-white text-xs font-bold px-2 py-0.5 rounded-full">
          x{card.quantity}
        </span>
      )}

      {/* Extras badge (Foil, Promo) */}
      {card.extras && (
        <span className="absolute top-2 left-2 z-10 bg-amber-600/90 text-white text-xs font-bold px-2 py-0.5 rounded-full">
          {card.extras}
        </span>
      )}

      {/* Card image */}
      <div className="aspect-[5/7] bg-gradient-to-br from-tcg-card-alt to-tcg-card flex items-center justify-center overflow-hidden">
        {showImage ? (
          <img
            src={currentUrl}
            alt={displayName}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => {
              if (!imgError) {
                setImgError(true);
              } else {
                setFallbackError(true);
              }
            }}
          />
        ) : (
          <svg
            className="h-12 w-12 text-tcg-dimmed"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        )}
      </div>

      {/* Card info */}
      <div className="p-3">
        <h3
          className="text-sm font-semibold text-white truncate group-hover:text-tcg-secondary transition-colors"
          title={displayName}
        >
          {displayName}
        </h3>

        {!compact && (
          <div className="flex items-center gap-2 mt-1">
            {card.set_code && (
              <span className="inline-block px-1.5 py-0.5 text-xs font-mono bg-tcg-card-alt text-tcg-muted rounded-tcg-sm">
                {card.set_code}
              </span>
            )}
            {card.collector_number && (
              <span className="text-xs text-tcg-dimmed">
                #{card.collector_number}
              </span>
            )}
            {card.rarity && (
              <span className={`text-xs font-bold ${RARITY_COLORS[card.rarity] || "text-tcg-muted"}`}>
                {RARITY_LABEL_KEYS[card.rarity] ? t(RARITY_LABEL_KEYS[card.rarity]) : card.rarity}
              </span>
            )}
          </div>
        )}

        <div className="flex items-center justify-between mt-2">
          <p
            className={`text-sm font-bold ${card.latest_price != null ? "text-tcg-secondary" : "text-tcg-dimmed"}`}
            data-testid="card-price"
          >
            {formatCurrency(card.latest_price, currencyOverride || "BRL")}
          </p>
          {!compact && (
            <div className="flex items-center gap-1 text-xs text-tcg-muted">
              {card.quality && <span>{card.quality}</span>}
              {card.language && <span className="text-tcg-dimmed">({card.language})</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // All collection cards link to the collection detail page
  return <Link to={`/collection/${card.id}`}>{inner}</Link>;
}

export function MyCollection() {
  const { t } = useTranslation();

  useEffect(() => {
    document.title = `${t("collection.title")} | TCG Market`;
  }, [t]);

  const { currency } = useCurrency();
  const { gridSize, setGridSize } = useGridSize();

  const [searchParams, setSearchParams] = useSearchParams();
  const [searchTerm, setSearchTerm] = useState(searchParams.get("name") ?? "");
  const [selectedSet, setSelectedSet] = useState<string | null>(searchParams.get("set") ?? null);
  const [sortBy, setSortBy] = useState(searchParams.get("sort") ?? "name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">((searchParams.get("dir") as "asc" | "desc") ?? "asc");
  const [cards, setCards] = useState<CollectionCard[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<CollectionSummary | null>(null);
  const [setOptions, setSetOptions] = useState<{ label: string; value: string }[]>([]);

  const debouncedSearch = useDebounce(searchTerm, 300);
  const fetchIdRef = useRef(0);

  // Load summary and sets on mount (and when currency changes)
  useEffect(() => {
    fetchCollectionSummary({ currency }).then((res) => {
      if (res.data) setSummary(res.data);
    });
    fetchCollectionSets().then((res) => {
      if (res.data) {
        setSetOptions(
          res.data.map((s) => ({
            label: s.set_name || s.set_code,
            value: s.set_code,
          })),
        );
      }
    });
  }, [currency]);

  // Sync URL params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (debouncedSearch) params.name = debouncedSearch;
    if (selectedSet) params.set = selectedSet;
    if (sortBy !== "name") params.sort = sortBy;
    if (sortDir !== "asc") params.dir = sortDir;
    setSearchParams(params, { replace: true });
  }, [debouncedSearch, selectedSet, sortBy, sortDir, setSearchParams]);

  // Build API params (shared between initial fetch and load-more)
  const buildParams = useCallback(
    (currentOffset: number): Record<string, string> => {
      const params: Record<string, string> = {
        limit: String(DEFAULT_PAGE_LIMIT),
        offset: String(currentOffset),
      };
      if (debouncedSearch) params.name = debouncedSearch;
      if (selectedSet) params.set = selectedSet;
      // For price sorting, sort client-side — don't pass sort params to API
      if (sortBy !== "price") {
        params.sort_by = sortBy;
        params.sort_dir = sortDir;
      }
      if (currency !== "BRL") {
        params.currency = currency;
      }
      return params;
    },
    [debouncedSearch, selectedSet, sortBy, sortDir, currency],
  );

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
          setHasMore(total != null ? data.length < total : data.length >= DEFAULT_PAGE_LIMIT);
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
  }, [debouncedSearch, selectedSet, sortBy, sortDir, currency, buildParams]);

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
          setHasMore(total != null ? newOffset < total : data.length >= DEFAULT_PAGE_LIMIT);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : t("common.unknownError"));
      })
      .finally(() => setLoadingMore(false));
  }, [hasMore, loadingMore, offset, buildParams]);

  const sentinelRef = useInfiniteScroll(handleLoadMore, {
    enabled: hasMore && !loadingMore,
  });

  const handleClearFilters = useCallback(() => {
    setSearchTerm("");
    setSelectedSet(null);
  }, []);

  const handleSortChange = useCallback((newSortBy: string, newSortDir: "asc" | "desc") => {
    setSortBy(newSortBy);
    setSortDir(newSortDir);
  }, []);

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
    <div data-testid="page-collection">
      <h2 className="text-2xl font-bold text-white mb-6">{t("collection.title")}</h2>

      {/* Summary KPIs */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <KpiCard title={t("collection.uniqueCards")} value={String(summary.total_unique)} />
          <KpiCard title={t("collection.totalCards")} value={String(summary.total_cards)} />
          <KpiCard title={t("collection.sets")} value={String(summary.sets_count)} />
          <KpiCard
            title={t("collection.estValue")}
            value={summary.total_value ? formatCurrency(summary.total_value, currency) : t("common.noData")}
            icon={<CurrencyIndicator currency={currency} size={20} />}
          />
        </div>
      )}

      {/* Search, sort, and filters */}
      <div className="space-y-4 mb-6">
        <div className="flex gap-3 items-center">
          <div className="flex-1">
            <SearchBar value={searchTerm} onChange={setSearchTerm} />
          </div>
          <SortSelect
            options={COLLECTION_SORT_OPTIONS}
            value={`${sortBy}-${sortDir}`}
            onChange={handleSortChange}
          />
        </div>
        {setOptions.length > 0 && (
          <SetIconFilter options={setOptions} selected={selectedSet} onSelect={setSelectedSet} />
        )}
        <div className="flex justify-end">
          <GridSizeToggle value={gridSize} onChange={setGridSize} />
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorBanner message={error} variant="inline" />
        </div>
      )}

      {loading && (
        <div
          className={`grid ${GRID_SIZE_CONFIG[gridSize].gridClasses}`}
          data-testid="skeleton-grid"
        >
          {Array.from({ length: 12 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!loading && !error && cards.length === 0 && (
        <EmptyState
          message={t("collection.emptyCollection")}
          action={{ label: t("common.clearFilters"), onClick: handleClearFilters }}
        />
      )}

      {!loading && cards.length > 0 && (
        <>
          <div
            className={`grid ${GRID_SIZE_CONFIG[gridSize].gridClasses}`}
            data-testid="collection-grid"
          >
            {sortedCards.map((card) => (
              <CollectionCardTile key={card.id} card={card} compact={GRID_SIZE_CONFIG[gridSize].compact} currencyOverride={currency} />
            ))}
          </div>
          <div ref={sentinelRef} data-testid="scroll-sentinel" />
          {loadingMore && (
            <div className="flex justify-center mt-4" data-testid="loading-more">
              <div className="h-6 w-6 border-2 border-tcg-secondary border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
