import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { expressInterest, fetchListings, type MarketplaceListing } from "../api/marketplace";
import { Breadcrumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { TradeInterestModal } from "../components/TradeInterestModal";
import { SearchBar } from "../components/SearchBar";
import { SkeletonCard } from "../components/Skeleton";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { useDebounce } from "../hooks/useDebounce";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

function MarketplaceCardTile({
  listing,
  onInterest,
}: {
  listing: MarketplaceListing;
  onInterest: (listing: MarketplaceListing) => void;
}) {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const { getCardName } = useCardName();
  const [imgError, setImgError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);

  const displayName = getCardName(listing.card_name_en, listing.card_name_pt, t("common.unknownCard"));
  const primaryUrl = scryfallImageUrl(listing.set_code, listing.collector_number);
  const fallbackUrl = listing.card_name_en ? scryfallImageByName(listing.card_name_en) : null;
  const currentUrl = imgError && fallbackUrl ? fallbackUrl : primaryUrl;
  const showImage = !(imgError && (fallbackError || !fallbackUrl));

  return (
    <div
      className="group block bg-slate-800 rounded-lg overflow-hidden border border-slate-600
        hover:border-cyan-400/50 transition-all duration-300 hover:scale-[1.02] hover:shadow-lg relative"
      data-testid={`marketplace-card-${listing.entry_id}`}
    >
      {listing.quantity > 1 && (
        <span className="absolute top-2 right-2 z-10 bg-indigo-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
          x{listing.quantity}
        </span>
      )}

      <div className="aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center overflow-hidden">
        {showImage ? (
          <img
            src={currentUrl}
            alt={displayName}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => {
              if (!imgError) setImgError(true);
              else setFallbackError(true);
            }}
          />
        ) : (
          <span className="text-slate-500 text-xs text-center px-2">{displayName}</span>
        )}
      </div>

      <div className="p-3 space-y-1.5">
        <h3 className="text-sm font-semibold text-white truncate" title={displayName}>
          {displayName}
        </h3>
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{listing.set_code.toUpperCase()} #{listing.collector_number}</span>
          {listing.rarity && (
            <span className={
              listing.rarity === "M" ? "text-amber-400" :
              listing.rarity === "R" ? "text-yellow-500" :
              listing.rarity === "U" ? "text-slate-400" : "text-slate-500"
            }>
              {listing.rarity}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-cyan-400">
            {listing.latest_price != null
              ? formatCurrency(listing.latest_price, currency)
              : t("common.noData")}
          </span>
          <span className="text-xs text-amber-400" title={t("marketplace.estimatedFee", { fee: listing.estimated_fee })}>
            {listing.estimated_fee} {t("marketplace.tokens")}
          </span>
        </div>

        <button
          type="button"
          onClick={() => onInterest(listing)}
          className="w-full mt-1.5 px-3 py-1.5 text-xs font-medium bg-cyan-600 hover:bg-cyan-500
            text-white rounded-md transition-colors duration-200"
          data-testid={`interest-btn-${listing.entry_id}`}
        >
          {t("marketplace.interested")}
        </button>

        <div className="text-[10px] text-slate-500 text-center mt-1">
          {listing.share_code.slice(0, 8)}...
        </div>
      </div>
    </div>
  );
}

export function Marketplace() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState(searchParams.get("search") || "");
  const debouncedSearch = useDebounce(searchTerm, 300);

  const loadListings = useCallback(async (search?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = { limit: "40" };
      if (search) params.search = search;
      const resp = await fetchListings(params);
      setListings(resp.listings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load listings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadListings(debouncedSearch || undefined);
    if (debouncedSearch) {
      setSearchParams({ search: debouncedSearch }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  }, [debouncedSearch, loadListings, setSearchParams]);

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
          to="/marketplace/my-trades"
          className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {t("marketplace.myTrades")}
        </Link>
      </div>

      <div className="mb-6">
        <SearchBar value={searchTerm} onChange={setSearchTerm} />
      </div>

      {error && <ErrorBanner message={error} onRetry={() => loadListings(debouncedSearch || undefined)} />}

      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!loading && !error && listings.length === 0 && (
        <EmptyState message={t("marketplace.noListings")} />
      )}

      {!loading && listings.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {listings.map((listing) => (
            <MarketplaceCardTile
              key={`${listing.share_code}-${listing.entry_id}`}
              listing={listing}
              onInterest={handleInterest}
            />
          ))}
        </div>
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
