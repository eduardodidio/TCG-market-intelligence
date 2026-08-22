import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { fetchCollectionBanned } from "../api/banEngine";
import { fetchCollection, fetchCollectionSummary, fetchCollectionSets, refreshCardPrice } from "../api/collection";
import { BanAlertBanner } from "../components/BanAlertBanner";
import { BanBadge } from "../components/BanBadge";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { GridSizeToggle } from "../components/GridSizeToggle";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
import { KpiCard } from "../components/KpiCard";
import { ScanProgressBar } from "../components/ScanProgressBar";
import { SearchBar } from "../components/SearchBar";
import { SetIconFilter } from "../components/SetIconFilter";
import { SkeletonCard } from "../components/Skeleton";
import { SortSelect, COLLECTION_SORT_OPTIONS } from "../components/SortSelect";
import { useDebounce } from "../hooks/useDebounce";
import { useGridSize } from "../hooks/useGridSize";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import type { BannedCollectionCard, CollectionCard, CollectionSummary } from "../types/api";
import { DEFAULT_PAGE_LIMIT, GRID_SIZE_CONFIG } from "../utils/constants";
import { useCardName } from "../hooks/useCardName";
import { useCollectionRefresh } from "../hooks/useCollectionRefresh";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

const HIGHLIGHT_DURATION_MS = 2_000;

const RARITY_COLORS: Record<string, string> = {
  M: "text-amber-400",
  R: "text-yellow-500",
  U: "text-slate-400",
  C: "text-slate-500",
};

const RARITY_LABEL_KEYS: Record<string, string> = {
  M: "rarity.mythic",
  R: "rarity.rare",
  U: "rarity.uncommon",
  C: "rarity.common",
};

function CollectionCardTile({ card, compact = false, currencyOverride, onRefresh, highlightColor, banStatus, banRecentlyChanged }: { card: CollectionCard; compact?: boolean; currencyOverride?: string; onRefresh?: (entryId: number, currency?: string) => Promise<void>; highlightColor?: "green" | "amber"; banStatus?: "banned" | "restricted"; banRecentlyChanged?: boolean }) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();
  const displayName = getCardName(card.name_en, card.name_pt, t("common.unknownCard"));
  const [imgError, setImgError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Primary image: backend-provided URL (Scryfall by set/number)
  // Fallback: Scryfall by exact card name
  const primaryUrl = card.image_url || scryfallImageUrl(card.set_code, card.collector_number);
  const fallbackUrl = card.name_en ? scryfallImageByName(card.name_en) : null;
  const currentUrl = imgError && fallbackUrl ? fallbackUrl : primaryUrl;
  const showImage = !(imgError && (fallbackError || !fallbackUrl));

  const inner = (
    <div
      className={`group block bg-slate-800 rounded-lg overflow-hidden
        border transition-all duration-500 hover:scale-[1.02] hover:shadow-lg relative cursor-pointer
        ${banRecentlyChanged ? "ring-2 ring-red-400/60 border-red-400/50" : highlightColor === "green" ? "ring-2 ring-emerald-400/60 border-emerald-400/50" : highlightColor === "amber" ? "ring-2 ring-amber-400/40 border-amber-400/40" : "border-slate-600 hover:border-cyan-400/50"}`}
      data-testid={`collection-card-${card.id}`}
    >
      {/* Quantity badge */}
      {card.quantity > 1 && (
        <span className="absolute top-2 right-2 z-10 bg-indigo-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
          x{card.quantity}
        </span>
      )}

      {/* Extras badge (Foil, Promo) */}
      {card.extras && (
        <span className="absolute top-2 left-2 z-10 bg-amber-600/90 text-white text-xs font-bold px-2 py-0.5 rounded-full">
          {card.extras}
        </span>
      )}

      {/* Ban badge */}
      {banStatus && (
        <span className={`absolute ${card.extras ? "top-8" : "top-2"} left-2 z-10`}>
          <BanBadge status={banStatus} recentlyChanged={banRecentlyChanged} />
        </span>
      )}

      {/* Card image */}
      <div className="aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center overflow-hidden relative">
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
            className="h-12 w-12 text-slate-500"
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

        {/* Refresh button overlay */}
        {card.card_id != null && onRefresh && (
          <button
            data-testid={`refresh-card-${card.id}`}
            onClick={async (e) => {
              e.preventDefault();
              e.stopPropagation();
              setRefreshing(true);
              try {
                await onRefresh(card.id, currencyOverride);
              } finally {
                setRefreshing(false);
              }
            }}
            disabled={refreshing}
            title={t("collection.refresh")}
            className="absolute bottom-2 right-2 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-black/60 text-slate-300 hover:text-cyan-400 hover:bg-black/80 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-100 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <svg
              className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Card info */}
      <div className="p-3">
        <h3
          className="text-sm font-semibold text-white truncate group-hover:text-cyan-400 transition-colors"
          title={displayName}
        >
          {displayName}
        </h3>

        {!compact && (
          <div className="flex items-center gap-2 mt-1">
            {card.set_code && (
              <span className="inline-block px-1.5 py-0.5 text-xs font-mono bg-slate-700 text-slate-400 rounded">
                {card.set_code}
              </span>
            )}
            {card.collector_number && (
              <span className="text-xs text-slate-500">
                #{card.collector_number}
              </span>
            )}
            {card.rarity && (
              <span className={`text-xs font-bold ${RARITY_COLORS[card.rarity] || "text-slate-400"}`}>
                {RARITY_LABEL_KEYS[card.rarity] ? t(RARITY_LABEL_KEYS[card.rarity]) : card.rarity}
              </span>
            )}
          </div>
        )}

        <div className="flex items-center justify-between mt-2">
          <p
            className={`text-sm font-bold ${card.latest_price != null ? "text-cyan-400" : "text-slate-500"}`}
            data-testid="card-price"
          >
            {formatCurrency(card.latest_price, currencyOverride || "BRL")}
          </p>
          {!compact && (
            <div className="flex items-center gap-1 text-xs text-slate-400">
              {card.quality && <span>{card.quality}</span>}
              {card.language && <span className="text-slate-500">({card.language})</span>}
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
  const [refreshKey, setRefreshKey] = useState(0);
  const [bannedCards, setBannedCards] = useState<BannedCollectionCard[]>([]);
  const [banDismissed, setBanDismissed] = useState(() => sessionStorage.getItem("ban_alert_dismissed") === "1");
  const [recentlyScanned, setRecentlyScanned] = useState<Map<string, { color: "green" | "amber"; timer: ReturnType<typeof setTimeout> }>>(new Map());
  const [priceFoundCount, setPriceFoundCount] = useState(0);
  const [scanStartTime, setScanStartTime] = useState(0);

  const debouncedSearch = useDebounce(searchTerm, 300);
  const fetchIdRef = useRef(0);

  const handleRefreshComplete = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const {
    isRefreshing,
    progress: refreshProgress,
    error: refreshError,
    isDone: refreshDone,
    lastScannedCard,
    startRefresh: rawStartRefresh,
    cancelRefresh,
  } = useCollectionRefresh(handleRefreshComplete);

  // Wrap startRefresh to reset scan tracking state
  const startRefresh = useCallback(async () => {
    setPriceFoundCount(0);
    setScanStartTime(Date.now());
    setRecentlyScanned(new Map());
    await rawStartRefresh();
  }, [rawStartRefresh]);

  // Live card updates: when lastScannedCard changes, update the local cards state
  useEffect(() => {
    if (!lastScannedCard || !lastScannedCard.externalId) return;

    const { externalId, priceFound, price } = lastScannedCard;

    // Track price-found count
    if (priceFound) {
      setPriceFoundCount((c) => c + 1);
    }

    // Update card price in local state (match by card_id via source card external_id)
    if (priceFound && price != null) {
      setCards((prev) =>
        prev.map((c) => {
          // CollectionCard doesn't have external_id directly, but we can try name matching
          // or card_id matching. For now we match by name_en if available.
          if (c.name_en && c.name_en === lastScannedCard.name) {
            return { ...c, latest_price: price };
          }
          return c;
        }),
      );
    }

    // Add highlight
    const color: "green" | "amber" = priceFound ? "green" : "amber";
    setRecentlyScanned((prev) => {
      const next = new Map(prev);
      // Clear existing timer for this card
      const existing = next.get(externalId);
      if (existing) clearTimeout(existing.timer);
      const timer = setTimeout(() => {
        setRecentlyScanned((m) => {
          const updated = new Map(m);
          updated.delete(externalId);
          return updated;
        });
      }, HIGHLIGHT_DURATION_MS);
      next.set(externalId, { color, timer });
      return next;
    });
  }, [lastScannedCard]);

  // Clean up highlight timers on unmount
  useEffect(() => {
    return () => {
      recentlyScanned.forEach(({ timer }) => clearTimeout(timer));
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Build lookup map for banned cards: card_id -> worst status + recentlyChanged
  const bannedCardMap = useMemo(() => {
    const map = new Map<number, { status: "banned" | "restricted"; recentlyChanged: boolean }>();
    for (const bc of bannedCards) {
      const existing = map.get(bc.card_id);
      // Keep worst status: banned > restricted
      if (!existing || (bc.status === "banned" && existing.status !== "banned")) {
        map.set(bc.card_id, {
          status: bc.status as "banned" | "restricted",
          recentlyChanged: bc.recently_changed || (existing?.recentlyChanged ?? false),
        });
      } else if (bc.recently_changed && existing) {
        map.set(bc.card_id, { ...existing, recentlyChanged: true });
      }
    }
    return map;
  }, [bannedCards]);

  const handleBanDismiss = useCallback(() => {
    setBanDismissed(true);
    sessionStorage.setItem("ban_alert_dismissed", "1");
  }, []);

  // Load summary, sets, and banned cards on mount (and when currency/refreshKey changes)
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
    fetchCollectionBanned().then((res) => {
      if (res.data) setBannedCards(res.data);
    });
  }, [currency, refreshKey]);

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
  }, [debouncedSearch, selectedSet, sortBy, sortDir, currency, buildParams, refreshKey]);

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

  const handleCardRefresh = useCallback(async (entryId: number, cardCurrency?: string) => {
    const params: Record<string, string> = {};
    const cur = cardCurrency || currency;
    if (cur !== "BRL") params.currency = cur;
    const res = await refreshCardPrice(entryId, Object.keys(params).length > 0 ? params : undefined);
    if (res.data) {
      setCards((prev) =>
        prev.map((c) =>
          c.id === entryId ? { ...c, latest_price: res.data!.latest_price } : c,
        ),
      );
    }
  }, [currency]);

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

      {/* Ban alert banner */}
      {summary && !banDismissed && (summary.banned_count > 0 || (bannedCards.length > 0)) && (
        <div className="mb-6">
          <BanAlertBanner
            bannedCount={summary.banned_count}
            restrictedCount={0}
            recentlyChangedCount={summary.recently_changed_count}
            onDismiss={handleBanDismiss}
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
        <div className="flex justify-end items-center gap-3">
          {/* Refresh All button (only show when not refreshing) */}
          {!isRefreshing && !refreshDone && !refreshError && (
            <button
              type="button"
              onClick={startRefresh}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
                bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg
                transition-colors duration-200"
              data-testid="refresh-all-btn"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span className="hidden sm:inline">{t("collection.refreshAll")}</span>
            </button>
          )}

          <GridSizeToggle value={gridSize} onChange={setGridSize} />
        </div>

        {/* Enhanced progress bar */}
        {(isRefreshing || refreshDone || refreshError) && (
          <ScanProgressBar
            processed={refreshProgress?.processed ?? 0}
            total={refreshProgress?.total ?? 0}
            currentCardName={lastScannedCard?.name}
            priceFoundCount={priceFoundCount}
            startTime={scanStartTime}
            isRefreshing={isRefreshing}
            isDone={refreshDone}
            error={refreshError}
            onCancel={isRefreshing ? cancelRefresh : undefined}
          />
        )}
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
            {sortedCards.map((card) => {
              // Check if this card was recently scanned (match by name_en)
              let highlightColor: "green" | "amber" | undefined;
              for (const [, val] of recentlyScanned) {
                // Since we don't have external_id on CollectionCard, we match via name
                if (card.name_en && card.name_en === lastScannedCard?.name) {
                  highlightColor = val.color;
                  break;
                }
              }
              // Also check by iterating over all recently scanned entries
              if (!highlightColor) {
                recentlyScanned.forEach((val, extId) => {
                  // Try matching by external_id patterns if available
                  if (card.name_en && lastScannedCard?.externalId === extId && card.name_en === lastScannedCard?.name) {
                    highlightColor = val.color;
                  }
                });
              }
              const banInfo = card.card_id ? bannedCardMap.get(card.card_id) : undefined;
              return (
                <CollectionCardTile
                  key={card.id}
                  card={card}
                  compact={GRID_SIZE_CONFIG[gridSize].compact}
                  currencyOverride={currency}
                  onRefresh={handleCardRefresh}
                  highlightColor={highlightColor}
                  banStatus={banInfo?.status}
                  banRecentlyChanged={banInfo?.recentlyChanged}
                />
              );
            })}
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
