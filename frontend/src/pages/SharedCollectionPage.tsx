import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  expressInterest,
  fetchSharedCollection,
  type MarketplaceListing,
  type CollectionInfo,
} from "../api/marketplace";
import { Breadcrumb } from "../components/Breadcrumb";
import { CopyCodeButton } from "../components/CopyCodeButton";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { SearchBar } from "../components/SearchBar";
import { SkeletonCard } from "../components/Skeleton";
import { TradeInterestModal } from "../components/TradeInterestModal";
import { useAuth } from "../hooks/useAuth";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { useDebounce } from "../hooks/useDebounce";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

function SharedCardTile({
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
      data-testid={`shared-card-${listing.entry_id}`}
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
      </div>
    </div>
  );
}

export function SharedCollectionPage() {
  const { code } = useParams<{ code: string }>();
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [collectionInfo, setCollectionInfo] = useState<CollectionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearch = useDebounce(searchTerm, 300);

  const loadCollection = useCallback(
    async (search?: string) => {
      if (!code) return;
      setLoading(true);
      setError(null);
      setNotFound(false);
      try {
        const params: Record<string, string> = { limit: "40" };
        if (search) params.search = search;
        const resp = await fetchSharedCollection(code, params);
        setListings(resp.listings);
        setCollectionInfo(resp.collection_info);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to load collection";
        if (msg.includes("not found") || msg.includes("Not Found")) {
          setNotFound(true);
        } else {
          setError(msg);
        }
      } finally {
        setLoading(false);
      }
    },
    [code],
  );

  useEffect(() => {
    loadCollection(debouncedSearch || undefined);
  }, [debouncedSearch, loadCollection]);

  const [selectedListing, setSelectedListing] = useState<MarketplaceListing | null>(null);
  const [interestSuccess, setInterestSuccess] = useState(false);

  const handleInterest = useCallback(
    (listing: MarketplaceListing) => {
      if (!isAuthenticated) {
        navigate(`/login?redirect=/marketplace/share/${code}`);
        return;
      }
      setSelectedListing(listing);
      setInterestSuccess(false);
    },
    [isAuthenticated, navigate, code],
  );

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

  const formatDate = (iso: string | null) => {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleDateString();
    } catch {
      return iso;
    }
  };

  return (
    <div data-testid="page-shared-collection">
      <Breadcrumb
        items={[
          { label: t("nav.dashboard"), to: "/" },
          { label: t("nav.marketplace"), to: "/marketplace" },
          { label: code ? `${code.slice(0, 8)}...` : t("marketplace.sharedCollection") },
        ]}
      />

      {/* Not found */}
      {notFound && (
        <EmptyState
          title={t("marketplace.collectionNotFound")}
          actions={[
            {
              label: t("nav.marketplace"),
              onClick: () => navigate("/marketplace"),
            },
          ]}
        />
      )}

      {/* Error */}
      {error && <ErrorBanner message={error} onRetry={() => loadCollection(debouncedSearch || undefined)} />}

      {/* Header with stats */}
      {!notFound && !error && collectionInfo && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-2xl font-bold text-white">{t("marketplace.sharedCollection")}</h2>
            <Link
              to="/marketplace"
              className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              {t("nav.marketplace")}
            </Link>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm text-slate-400" data-testid="collection-stats">
            <span data-testid="total-cards">
              {t("marketplace.totalCards", { count: collectionInfo.total_cards })}
            </span>
            {collectionInfo.sets.length > 0 && (
              <span data-testid="collection-sets">
                {collectionInfo.sets.map((s) => s.toUpperCase()).join(", ")}
              </span>
            )}
            {collectionInfo.shared_at && (
              <span data-testid="shared-at">
                {t("marketplace.sharedSince", { date: formatDate(collectionInfo.shared_at) })}
              </span>
            )}
            {code && (
              <CopyCodeButton code={code} truncateAt={12} />
            )}
          </div>
        </div>
      )}

      {/* Search */}
      {!notFound && (
        <div className="mb-6">
          <SearchBar value={searchTerm} onChange={setSearchTerm} />
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* Empty collection */}
      {!loading && !error && !notFound && listings.length === 0 && (
        <EmptyState message={t("marketplace.emptyCollection")} />
      )}

      {/* Card grid */}
      {!loading && listings.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {listings.map((listing) => (
            <SharedCardTile
              key={`${listing.share_code}-${listing.entry_id}`}
              listing={listing}
              onInterest={handleInterest}
            />
          ))}
        </div>
      )}

      {/* Interest success toast */}
      {interestSuccess && (
        <div
          className="fixed bottom-6 right-6 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm z-40"
          data-testid="interest-success-toast"
        >
          {t("marketplace.expressInterest")} ✓
        </div>
      )}

      {/* Interest modal */}
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
