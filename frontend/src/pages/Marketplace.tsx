import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import {
  expressInterest,
  fetchListings,
  fetchListingSets,
  type ListingSet,
  type MarketplaceListing,
} from "../api/marketplace";
import { Breadcrumb } from "../components/Breadcrumb";
import { CardFilterBar } from "../components/CardFilterBar";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { TradeInterestModal } from "../components/TradeInterestModal";
import { SkeletonCard } from "../components/Skeleton";
import { MarketplaceCardTile } from "../components/MarketplaceCardTile";
import { useCardListFilters } from "../hooks/useCardListFilters";
import { useGridSize } from "../hooks/useGridSize";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import { GRID_SIZE_CONFIG } from "../utils/constants";
import { MARKETPLACE_SORT_OPTIONS } from "../utils/tradeSortOptions";

const PAGE_LIMIT = 40;

export function Marketplace() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const { gridSize, setGridSize } = useGridSize();
  const {
    search,
    setSearch,
    debouncedSearch,
    selectedSet,
    setSelectedSet,
    sortBy,
    sortDir,
    sortValue,
    setSort,
  } = useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" });

  useEffect(() => {
    const legacySearch = searchParams.get("search");
    if (legacySearch && !searchParams.get("name")) {
      setSearch(legacySearch);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [setOptions, setSetOptions] = useState<{ label: string; value: string }[]>([]);

  const fetchIdRef = useRef(0);

  const buildParams = useCallback(
    (currentOffset: number): Record<string, string> => {
      const params: Record<string, string> = {
        limit: String(PAGE_LIMIT),
        offset: String(currentOffset),
        sort_by: sortBy,
        sort_dir: sortDir,
      };
      if (debouncedSearch) params.search = debouncedSearch;
      if (selectedSet) params.set_code = selectedSet;
      return params;
    },
    [debouncedSearch, selectedSet, sortBy, sortDir],
  );

  const loadInitial = useCallback(() => {
    fetchIdRef.current += 1;
    const currentId = fetchIdRef.current;

    setLoading(true);
    setError(null);
    setOffset(0);
    setHasMore(false);

    fetchListings(buildParams(0))
      .then((resp) => {
        if (currentId !== fetchIdRef.current) return;
        setListings(resp.listings);
        setOffset(resp.listings.length);
        setHasMore(resp.listings.length === PAGE_LIMIT);
      })
      .catch((err: unknown) => {
        if (currentId !== fetchIdRef.current) return;
        setError(err instanceof Error ? err.message : "Failed to load listings");
      })
      .finally(() => {
        if (currentId === fetchIdRef.current) setLoading(false);
      });
  }, [buildParams]);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    fetchListingSets()
      .then((resp) => {
        setSetOptions(
          resp.sets.map((s: ListingSet) => ({
            label: s.set_name || s.set_code.toUpperCase(),
            value: s.set_code,
          })),
        );
      })
      .catch(() => {
        setSetOptions([]);
      });
  }, []);

  const handleLoadMore = useCallback(() => {
    if (!hasMore || loadingMore) return;
    setLoadingMore(true);
    const currentId = fetchIdRef.current;

    fetchListings(buildParams(offset))
      .then((resp) => {
        if (currentId !== fetchIdRef.current) return;
        setListings((prev) => [...prev, ...resp.listings]);
        setOffset(offset + resp.listings.length);
        setHasMore(resp.listings.length === PAGE_LIMIT);
      })
      .catch((err: unknown) => {
        if (currentId !== fetchIdRef.current) return;
        setError(err instanceof Error ? err.message : "Failed to load listings");
      })
      .finally(() => {
        if (currentId === fetchIdRef.current) setLoadingMore(false);
      });
  }, [hasMore, loadingMore, offset, buildParams]);

  const sentinelRef = useInfiniteScroll(handleLoadMore, {
    enabled: hasMore && !loadingMore,
  });

  const [selectedListing, setSelectedListing] = useState<MarketplaceListing | null>(null);
  const [interestSuccess, setInterestSuccess] = useState(false);

  const handleInterest = useCallback((listing: MarketplaceListing) => {
    setSelectedListing(listing);
    setInterestSuccess(false);
  }, []);

  const handleInterestSubmit = useCallback(
    async (message: string | undefined) => {
      if (!selectedListing) return;
      await expressInterest(
        selectedListing.share_code,
        selectedListing.entry_id,
        message,
      );
      setSelectedListing(null);
      setInterestSuccess(true);
      setTimeout(() => setInterestSuccess(false), 3000);
    },
    [selectedListing],
  );

  return (
    <div data-testid="page-marketplace">
      <Breadcrumb
        items={[
          { label: t("nav.dashboard"), to: "/" },
          { label: t("nav.marketplace") },
        ]}
      />
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">{t("marketplace.title")}</h2>
        <Link
          to={"/marketplace/my-trades"}
          className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {t("marketplace.myTrades")}
        </Link>
      </div>

      <CardFilterBar
        search={search}
        onSearchChange={setSearch}
        sortOptions={MARKETPLACE_SORT_OPTIONS}
        sortValue={sortValue}
        onSortChange={setSort}
        setOptions={setOptions}
        selectedSet={selectedSet}
        onSetSelect={setSelectedSet}
        gridSize={gridSize}
        onGridSizeChange={setGridSize}
      />

      {error && (
        <ErrorBanner
          message={error}
          onRetry={listings.length === 0 ? loadInitial : handleLoadMore}
        />
      )}

      {loading && (
        <div className={`grid ${GRID_SIZE_CONFIG[gridSize].gridClasses}`}>
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!loading && !error && listings.length === 0 && (
        <EmptyState message={t("marketplace.noListings")} />
      )}

      {!loading && listings.length > 0 && (
        <>
          <div className={`grid ${GRID_SIZE_CONFIG[gridSize].gridClasses}`}>
            {listings.map((listing) => (
              <MarketplaceCardTile
                key={`${listing.share_code}-${listing.entry_id}`}
                listing={listing}
                onInterest={handleInterest}
                compact={GRID_SIZE_CONFIG[gridSize].compact}
              />
            ))}
          </div>
          <div ref={sentinelRef} data-testid="marketplace-sentinel" />
          {loadingMore && (
            <div className={`grid ${GRID_SIZE_CONFIG[gridSize].gridClasses} mt-4`}>
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          )}
        </>
      )}

      {interestSuccess && (
        <div
          className="fixed bottom-6 right-6 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm z-40"
          data-testid="interest-success-toast"
        >
          {t("marketplace.expressInterest")} ✓
        </div>
      )}

      {selectedListing && (
        <TradeInterestModal
          listing={selectedListing}
          onSubmit={handleInterestSubmit}
          onCancel={() => setSelectedListing(null)}
        />
      )}
    </div>
  );
}
