import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { fetchCollection, fetchCollectionSummary, fetchCollectionSets } from "../api/collection";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { FilterChips } from "../components/FilterChips";
import { KpiCard } from "../components/KpiCard";
import { SearchBar } from "../components/SearchBar";
import { SkeletonCard } from "../components/Skeleton";
import { SortSelect, COLLECTION_SORT_OPTIONS } from "../components/SortSelect";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import type { CollectionCard, CollectionSummary } from "../types/api";
import { formatBRL } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";
import { DEFAULT_PAGE_LIMIT } from "../utils/constants";

const RARITY_COLORS: Record<string, string> = {
  M: "text-amber-400",
  R: "text-yellow-500",
  U: "text-slate-300",
  C: "text-slate-500",
};

const RARITY_LABELS: Record<string, string> = {
  M: "Mythic",
  R: "Rare",
  U: "Uncommon",
  C: "Common",
};

function CollectionCardTile({ card }: { card: CollectionCard }) {
  const displayName = card.name_en || card.name_pt || "Unknown Card";
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
      className="group block bg-slate-800 rounded-xl overflow-hidden
        border border-slate-700 hover:border-cyan-500/50
        transition-all duration-200 hover:scale-[1.02] relative cursor-pointer"
      data-testid={`collection-card-${card.id}`}
    >
      {/* Quantity badge */}
      {card.quantity > 1 && (
        <span className="absolute top-2 right-2 z-10 bg-indigo-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">
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
      <div className="aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center overflow-hidden">
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
            className="h-12 w-12 text-slate-600"
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
          className="text-sm font-semibold text-white truncate group-hover:text-cyan-400 transition-colors"
          title={displayName}
        >
          {displayName}
        </h3>

        <div className="flex items-center gap-2 mt-1">
          {card.set_code && (
            <span className="inline-block px-1.5 py-0.5 text-xs font-mono bg-slate-700 text-slate-300 rounded">
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
              {RARITY_LABELS[card.rarity] || card.rarity}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mt-2">
          <p
            className={`text-sm font-bold ${card.latest_price != null ? "text-cyan-400" : "text-slate-500"}`}
            data-testid="card-price"
          >
            {formatBRL(card.latest_price)}
          </p>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            {card.quality && <span>{card.quality}</span>}
            {card.language && <span className="text-slate-500">({card.language})</span>}
          </div>
        </div>
      </div>
    </div>
  );

  // All collection cards link to the collection detail page
  return <Link to={`/collection/${card.id}`}>{inner}</Link>;
}

export function MyCollection() {
  useEffect(() => {
    document.title = "My Collection | TCG Market";
  }, []);

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

  // Load summary and sets on mount
  useEffect(() => {
    fetchCollectionSummary().then((res) => {
      if (res.data) setSummary(res.data);
    });
    fetchCollectionSets().then((res) => {
      if (res.data) {
        setSetOptions(
          res.data.map((s) => ({
            label: s.set_name ? `${s.set_code} — ${s.set_name}` : s.set_code,
            value: s.set_code,
          })),
        );
      }
    });
  }, []);

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
      return params;
    },
    [debouncedSearch, selectedSet, sortBy, sortDir],
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
        setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        if (currentId === fetchIdRef.current) setLoading(false);
      });
  }, [debouncedSearch, selectedSet, sortBy, sortDir, buildParams]);

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
        setError(err instanceof Error ? err.message : "Unknown error");
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
      <h2 className="text-2xl font-bold text-white mb-6">My Collection</h2>

      {/* Summary KPIs */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <KpiCard title="Unique Cards" value={String(summary.total_unique)} />
          <KpiCard title="Total Cards" value={String(summary.total_cards)} />
          <KpiCard title="Sets" value={String(summary.sets_count)} />
          <KpiCard
            title="Est. Value"
            value={summary.total_value ? formatBRL(summary.total_value) : "--"}
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
          <FilterChips options={setOptions} selected={selectedSet} onSelect={setSelectedSet} />
        )}
      </div>

      {error && (
        <div className="mb-6">
          <ErrorBanner message={error} variant="inline" />
        </div>
      )}

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

      {!loading && !error && cards.length === 0 && (
        <EmptyState
          message="No cards in your collection. Import your CSV to get started."
          action={{ label: "Clear filters", onClick: handleClearFilters }}
        />
      )}

      {!loading && cards.length > 0 && (
        <>
          <div
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-4"
            data-testid="collection-grid"
          >
            {sortedCards.map((card) => (
              <CollectionCardTile key={card.id} card={card} />
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
