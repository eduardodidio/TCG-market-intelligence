import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { refreshCardPrice } from "../api/cards";
import { refreshCatalogSet } from "../api/catalog";
import { Breadcrumb } from "../components/Breadcrumb";
import { Card3DTilt } from "../components/Card3DTilt";
import { CardImage } from "../components/CardImage";
import { CardPreviewModal } from "../components/CardPreviewModal";
import { CreditConfirmModal } from "../components/CreditConfirmModal";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { GridSizeToggle } from "../components/GridSizeToggle";
import { SearchBar } from "../components/SearchBar";
import { SkeletonCard } from "../components/Skeleton";
import { useAuth } from "../hooks/useAuth";
import { useCatalogCards } from "../hooks/useCatalogCards";
import type { CatalogCard } from "../hooks/useCatalogCards";
import { useCatalogSets } from "../hooks/useCatalogSets";
import { useCatalogStats } from "../hooks/useCatalogStats";
import { useCardName } from "../hooks/useCardName";
import { useCredits } from "../hooks/useCredits";
import { useGridSize } from "../hooks/useGridSize";
import { usePriceRequestPolling } from "../hooks/usePriceRequestPolling";
import { useScrollRestoration } from "../hooks/useScrollRestoration";
import { GRID_SIZE_CONFIG } from "../utils/constants";
import { isPromoCard } from "../utils/promo";

const RARITY_OPTIONS = [
  { value: "C", label: "C" },
  { value: "U", label: "U" },
  { value: "R", label: "R" },
  { value: "M", label: "M" },
];

const COLOR_OPTIONS = [
  { value: "W", label: "W", color: "bg-amber-100 text-amber-800" },
  { value: "U", label: "U", color: "bg-blue-200 text-blue-800" },
  { value: "B", label: "B", color: "bg-gray-700 text-gray-100" },
  { value: "R", label: "R", color: "bg-red-200 text-red-800" },
  { value: "G", label: "G", color: "bg-green-200 text-green-800" },
  { value: "C", label: "C", color: "bg-slate-300 text-slate-700" },
];

const RARITY_COLORS: Record<string, string> = {
  c: "bg-slate-600 text-slate-300",
  u: "bg-slate-500 text-slate-200",
  r: "bg-amber-600 text-amber-100",
  m: "bg-orange-600 text-orange-100",
};

function RarityBadge({ rarity }: { rarity: string | null }) {
  if (!rarity) return null;
  const colorClass = RARITY_COLORS[rarity.toLowerCase()] ?? "bg-slate-600 text-slate-300";
  const label = rarity.charAt(0).toUpperCase();
  return (
    <span
      className={`inline-block px-1.5 py-0.5 text-xs font-bold rounded ${colorClass}`}
      title={rarity}
      data-testid="rarity-badge"
    >
      {label}
    </span>
  );
}

export function CatalogCardTile({ card, ownedView, compact }: { card: CatalogCard; ownedView?: boolean; compact?: boolean }) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();
  const { isAuthenticated } = useAuth();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [queued, setQueued] = useState(false);
  const [refreshError, setRefreshError] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [failed, setFailed] = useState(false);
  const displayName = getCardName(card.name_en, card.name_pt, t("common.unknownCard"));

  const isUnowned = ownedView && card.owned === false;

  // Poll for price request status after queuing
  const { status: requestStatus, isPolling } = usePriceRequestPolling({
    cardId: card.id,
    enabled: queued,
    onCompleted: () => {
      setQueued(false);
      setCompleted(true);
      setTimeout(() => setCompleted(false), 1500);
    },
    onFailed: () => {
      setQueued(false);
      setFailed(true);
      setTimeout(() => setFailed(false), 3000);
    },
  });

  const handleRefresh = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (refreshing || queued || completed || failed) return;

    setRefreshing(true);
    setRefreshError(false);
    try {
      const res = await refreshCardPrice(card.id);
      if (res.errors && res.errors.length > 0) {
        setRefreshError(true);
        setTimeout(() => setRefreshError(false), 3000);
        return;
      }
      if (res.data?.status === "queued") {
        setQueued(true);
      }
    } catch {
      setRefreshError(true);
      setTimeout(() => setRefreshError(false), 3000);
    } finally {
      setRefreshing(false);
    }
  };

  // Determine the visual state of the refresh button
  const pollingTimedOut = queued && !isPolling && requestStatus !== "completed" && requestStatus !== "failed";
  const showAlwaysVisible = refreshError || queued || completed || failed;

  const buttonColor = refreshError || failed
    ? "text-red-400"
    : completed
      ? "text-green-400"
      : queued
        ? pollingTimedOut
          ? "text-yellow-400"
          : "text-cyan-400"
        : "text-slate-300 hover:text-cyan-400";

  const buttonTitle = refreshError
    ? t("cards.priceRefreshError")
    : failed
      ? t("cards.priceUpdateFailed")
      : completed
        ? t("cards.priceUpdateCompleted")
        : pollingTimedOut
          ? t("cards.priceUpdateTimeout")
          : queued
            ? t("cards.priceUpdateProcessing")
            : t("credits.refreshCostTooltip", { cost: 1 });

  return (
    <Card3DTilt foil={false} className="w-full">
    <Link
      to={`/cards/${card.id}`}
      className={`group block bg-slate-800 rounded-lg overflow-hidden
        transition-all duration-200 hover:shadow-lg relative ${
          isUnowned
            ? "border border-dashed border-slate-600 opacity-40"
            : "border border-slate-600 hover:border-cyan-400/50"
        }`}
      data-testid={`catalog-card-${card.id}`}
    >
      {/* Refresh button overlay */}
      {isAuthenticated && (
        <button
          data-testid={`refresh-card-price-${card.id}`}
          onClick={handleRefresh}
          disabled={refreshing || queued || refreshError || completed || failed}
          title={buttonTitle}
          className={`absolute top-2 right-2 z-10 w-7 h-7 flex items-center justify-center rounded-full
            bg-black/60 ${buttonColor} hover:bg-black/80
            ${showAlwaysVisible ? "opacity-100" : "opacity-0 group-hover:opacity-100"} transition-all
            disabled:opacity-100 disabled:cursor-not-allowed
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400`}
        >
          {refreshError || failed ? (
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" data-testid="error-icon">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : completed ? (
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" data-testid="check-icon">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : queued && isPolling ? (
            <svg className="h-3.5 w-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" data-testid="spinner-icon">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          ) : pollingTimedOut ? (
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" data-testid="clock-icon">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <svg className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
        </button>
      )}

      {/* Card image with skeleton loading */}
      <div
        className={`aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800
          flex items-center justify-center overflow-hidden${card.image_uri ? " cursor-zoom-in" : ""}`}
        {...(card.image_uri
          ? {
              onClick: (e: React.MouseEvent) => {
                e.preventDefault();
                e.stopPropagation();
                setPreviewOpen(true);
              },
            }
          : {})}
      >
        <CardImage
          src={card.image_uri}
          alt={displayName}
        />
      </div>

      {/* Card info — hidden in compact mode */}
      {!compact && (
      <div className="p-3">
        <h3
          className="text-sm font-semibold text-white truncate group-hover:text-cyan-400 transition-colors"
          title={displayName}
        >
          {displayName}
        </h3>

        <div className="flex items-center gap-2 mt-1">
          {card.set_code && (
            <span className="inline-block px-1.5 py-0.5 text-xs font-mono bg-slate-700 text-slate-400 rounded">
              {card.set_code}
            </span>
          )}
          <RarityBadge rarity={card.rarity} />
        </div>

        {isUnowned && (
          <span
            className="inline-block mt-1 px-1.5 py-0.5 text-xs font-medium bg-slate-700 text-slate-400 rounded border border-dashed border-slate-500"
            data-testid="not-owned-badge"
          >
            {t("catalog.notOwned", { defaultValue: "Not owned" })}
          </span>
        )}

        {card.liga_price != null ? (
          <p className="mt-2 text-sm font-bold text-cyan-400" data-testid="card-price">
            R$ {card.liga_price.toFixed(2)}
          </p>
        ) : (
          <p className="mt-2 text-sm text-slate-500" data-testid="card-price">
            {t("common.noPriceData")}
          </p>
        )}
        {(queued && isPolling) && (
          <span className="text-xs text-cyan-400 mt-1 block" data-testid="queued-feedback">
            {t("cards.priceUpdateProcessing")}
          </span>
        )}
        {completed && (
          <span className="text-xs text-green-400 mt-1 block" data-testid="completed-feedback">
            {t("cards.priceUpdateCompleted")}
          </span>
        )}
        {failed && (
          <span className="text-xs text-red-400 mt-1 block" data-testid="failed-feedback">
            {t("cards.priceUpdateFailed")}
          </span>
        )}
        {refreshError && (
          <span className="text-xs text-red-400 mt-1 block" data-testid="refresh-error-feedback">
            {t("cards.priceRefreshError")}
          </span>
        )}
      </div>
      )}
    </Link>
    {previewOpen && card.image_uri && (
      <CardPreviewModal
        imageUrl={card.image_uri}
        cardName={displayName}
        isPromo={isPromoCard(card.set_code, null)}
        onClose={() => setPreviewOpen(false)}
      />
    )}
    </Card3DTilt>
  );
}

export function CatalogPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { gridSize, setGridSize } = useGridSize();

  useScrollRestoration("catalog");

  useEffect(() => {
    document.title = `${t("catalog.title")} | TCG Market`;
  }, [t]);

  // Owned view mode (from set completion click)
  const ownedView = searchParams.get("owned_view") === "1";

  // Initialize filters from URL search params
  const [searchTerm, setSearchTerm] = useState(searchParams.get("name") ?? "");
  const [selectedSet, setSelectedSet] = useState(searchParams.get("set_code") ?? "");
  const [selectedRarities, setSelectedRarities] = useState<Set<string>>(
    () => new Set(searchParams.get("rarity")?.split(",").filter(Boolean) ?? []),
  );
  const [selectedColors, setSelectedColors] = useState<Set<string>>(
    () => new Set(searchParams.get("color")?.split(",").filter(Boolean) ?? []),
  );
  const [hasPrice, setHasPrice] = useState(searchParams.get("has_price") ?? "");
  const [sortBy, setSortBy] = useState(searchParams.get("sort_by") ?? "name");
  const [sortDir, setSortDir] = useState(searchParams.get("sort_dir") ?? "asc");
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Sync filters to URL search params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (searchTerm) params.name = searchTerm;
    if (selectedSet) params.set_code = selectedSet;
    if (selectedRarities.size > 0) params.rarity = [...selectedRarities].join(",");
    if (selectedColors.size > 0) params.color = [...selectedColors].join(",");
    if (hasPrice) params.has_price = hasPrice;
    if (sortBy && sortBy !== "name") params.sort_by = sortBy;
    if (sortDir && sortDir !== "asc") params.sort_dir = sortDir;
    if (ownedView) params.owned_view = "1";
    setSearchParams(params, { replace: true });
  }, [searchTerm, selectedSet, selectedRarities, selectedColors, hasPrice, sortBy, sortDir, setSearchParams]);

  const filters = {
    name: searchTerm,
    set_code: selectedSet,
    rarity: [...selectedRarities].join(","),
    color: [...selectedColors].join(","),
    has_price: hasPrice,
    min_price: "",
    max_price: "",
    sort_by: sortBy,
    sort_dir: sortDir,
    with_ownership: ownedView ? "true" : "",
  };

  const { cards, total, loading, loadingMore, error, hasMore, loadMore } = useCatalogCards(filters);
  const { sets } = useCatalogSets();
  const { stats } = useCatalogStats();
  const { isAuthenticated } = useAuth();
  const { balance, bonusEligible, claimBonus, refetch: refetchCredits } = useCredits();

  // Refresh All Set state
  const [scanModalOpen, setScanModalOpen] = useState(false);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanFeedback, setScanFeedback] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  // Find the card count for the selected set
  const selectedSetInfo = sets.find((s) => s.set_code === selectedSet);
  const selectedSetCardCount = selectedSetInfo?.card_count ?? 0;

  const handleRefreshAllSet = useCallback(async () => {
    if (!selectedSet) return;
    setScanLoading(true);
    setScanError(null);
    setScanFeedback(null);
    try {
      const res = await refreshCatalogSet(selectedSet);
      if (res.errors && res.errors.length > 0) {
        setScanError(res.errors.map((e) => e.message).join("; "));
      } else if (res.data) {
        setScanFeedback(
          t("catalog.scanQueued", {
            count: res.data.card_count,
            set: res.data.set_code,
            defaultValue: "Queued {{count}} cards from {{set}} for price update",
          }),
        );
        refetchCredits();
      }
    } catch {
      setScanError(t("catalog.scanError", { defaultValue: "Failed to queue scan" }));
    } finally {
      setScanLoading(false);
      setScanModalOpen(false);
      // Clear feedback after 8 seconds
      setTimeout(() => {
        setScanFeedback(null);
        setScanError(null);
      }, 8000);
    }
  }, [selectedSet, t, refetchCredits]);

  const toggleRarity = useCallback((rarity: string) => {
    setSelectedRarities((prev) => {
      const next = new Set(prev);
      if (next.has(rarity)) {
        next.delete(rarity);
      } else {
        next.add(rarity);
      }
      return next;
    });
  }, []);

  const toggleColor = useCallback((color: string) => {
    setSelectedColors((prev) => {
      const next = new Set(prev);
      if (next.has(color)) {
        next.delete(color);
      } else {
        next.add(color);
      }
      return next;
    });
  }, []);

  const handleClearFilters = useCallback(() => {
    setSearchTerm("");
    setSelectedSet("");
    setSelectedRarities(new Set());
    setSelectedColors(new Set());
    setHasPrice("");
    setSortBy("name");
    setSortDir("asc");
  }, []);

  const hasActiveFilters =
    searchTerm !== "" ||
    selectedSet !== "" ||
    selectedRarities.size > 0 ||
    selectedColors.size > 0 ||
    hasPrice !== "";

  const setOptions = sets.map((s) => ({
    value: s.set_code,
    label: `${s.set_code} (${s.card_count})`,
  }));

  return (
    <div data-testid="page-catalog">
      <Breadcrumb
        items={[
          { label: t("nav.dashboard"), to: "/" },
          { label: t("catalog.title") },
        ]}
      />

      <h2 className="text-2xl font-bold text-white mb-2">{t("catalog.title")}</h2>

      {/* Stats summary */}
      {stats && (
        <p className="text-sm text-slate-400 mb-6" data-testid="catalog-stats">
          {t("catalog.statsLine", {
            cards: stats.total_cards.toLocaleString(),
            sets: stats.total_sets.toLocaleString(),
            priced: stats.cards_with_price.toLocaleString(),
          })}
        </p>
      )}

      {/* Search and filters — sticky bar */}
      <div className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur-sm pb-4 pt-2 -mx-6 px-6 border-b border-slate-700/50 space-y-4 mb-6" data-testid="sticky-filter-bar">
        <div className="flex gap-3 items-center">
          <div className="flex-1">
            <SearchBar
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder={t("catalog.searchPlaceholderBilingual")}
            />
          </div>
          <button
            onClick={() => setFiltersOpen((prev) => !prev)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              filtersOpen || hasActiveFilters
                ? "bg-cyan-500 text-white"
                : "bg-slate-800 text-slate-400 hover:text-white border border-slate-600"
            }`}
            data-testid="toggle-filters-btn"
            aria-expanded={filtersOpen}
          >
            {t("catalog.filters")}
            {hasActiveFilters && (
              <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-white text-cyan-600 rounded-full">
                {
                  [selectedSet, selectedRarities.size > 0, selectedColors.size > 0, hasPrice].filter(
                    Boolean,
                  ).length
                }
              </span>
            )}
          </button>
          <GridSizeToggle value={gridSize} onChange={setGridSize} />
        </div>

        {/* Collapsible filter section */}
        {filtersOpen && (
          <div
            className="bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-4"
            data-testid="filter-section"
          >
            {/* Set filter */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t("catalog.setFilter")}
              </label>
              <select
                value={selectedSet}
                onChange={(e) => setSelectedSet(e.target.value)}
                className="w-full bg-slate-700 text-white border border-slate-600 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
                data-testid="set-select"
              >
                <option value="">{t("common.all")}</option>
                {setOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Rarity chips */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t("catalog.rarityFilter")}
              </label>
              <div className="flex gap-2 flex-wrap">
                {RARITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => toggleRarity(opt.value)}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      selectedRarities.has(opt.value)
                        ? "bg-cyan-500 text-white"
                        : "bg-slate-700 text-slate-400 hover:text-white"
                    }`}
                    data-testid={`rarity-chip-${opt.value}`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Color identity chips */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t("catalog.colorFilter")}
              </label>
              <div className="flex gap-2 flex-wrap">
                {COLOR_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => toggleColor(opt.value)}
                    className={`px-3 py-1.5 rounded-full text-sm font-bold transition-colors ${
                      selectedColors.has(opt.value)
                        ? "ring-2 ring-cyan-400 " + opt.color
                        : opt.color + " opacity-50 hover:opacity-75"
                    }`}
                    data-testid={`color-chip-${opt.value}`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Has price toggle */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t("catalog.priceFilter")}
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setHasPrice(hasPrice === "true" ? "" : "true")}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    hasPrice === "true"
                      ? "bg-cyan-500 text-white"
                      : "bg-slate-700 text-slate-400 hover:text-white"
                  }`}
                  data-testid="has-price-btn"
                >
                  {t("catalog.hasPrice")}
                </button>
                <button
                  onClick={() => setHasPrice(hasPrice === "false" ? "" : "false")}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    hasPrice === "false"
                      ? "bg-cyan-500 text-white"
                      : "bg-slate-700 text-slate-400 hover:text-white"
                  }`}
                  data-testid="no-price-btn"
                >
                  {t("catalog.noPrice")}
                </button>
              </div>
            </div>

            {/* Sort options */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                {t("catalog.sortBy")}
              </label>
              <div className="flex gap-2">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-slate-700 text-white border border-slate-600 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
                  data-testid="sort-by-select"
                >
                  <option value="name">{t("catalog.sortName")}</option>
                  <option value="set_code">{t("catalog.sortSet")}</option>
                  <option value="price">{t("catalog.sortPrice")}</option>
                </select>
                <select
                  value={sortDir}
                  onChange={(e) => setSortDir(e.target.value)}
                  className="bg-slate-700 text-white border border-slate-600 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
                  data-testid="sort-dir-select"
                >
                  <option value="asc">{t("catalog.sortAsc")}</option>
                  <option value="desc">{t("catalog.sortDesc")}</option>
                </select>
              </div>
            </div>

            {/* Clear filters */}
            {hasActiveFilters && (
              <button
                onClick={handleClearFilters}
                className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                data-testid="clear-filters-btn"
              >
                {t("common.clearFilters")}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Owned view banner */}
      {ownedView && selectedSet && (
        <div
          className="mb-4 px-4 py-2 bg-cyan-900/30 border border-cyan-700/50 rounded-lg flex items-center justify-between"
          data-testid="owned-view-banner"
        >
          <span className="text-sm text-cyan-300">
            {t("catalog.ownedViewBanner", {
              set: selectedSet,
              defaultValue: "Showing set completion view for {{set}} -- owned cards at full opacity, unowned faded",
            })}
          </span>
          <Link
            to={`/collection?set=${selectedSet}`}
            className="text-sm text-cyan-400 hover:text-cyan-300 underline ml-4 shrink-0"
          >
            {t("catalog.backToCollection", { defaultValue: "Back to collection" })}
          </Link>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mb-6">
          <ErrorBanner message={error} variant="inline" />
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div
          className={`grid ${GRID_SIZE_CONFIG[gridSize].gridClasses}`}
          data-testid="skeleton-grid"
        >
          {Array.from({ length: 10 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && cards.length === 0 && (
        <EmptyState
          title={t("catalog.emptyTitle")}
          description={
            hasActiveFilters
              ? searchTerm
                ? `${t("catalog.emptyFiltered")} ${t("catalog.emptySearchHint")}`
                : t("catalog.emptyFiltered")
              : t("catalog.emptyDescription")
          }
          action={
            hasActiveFilters
              ? { label: t("common.clearFilters"), onClick: handleClearFilters }
              : undefined
          }
        />
      )}

      {/* Results count + Refresh All Set button */}
      {!loading && cards.length > 0 && (
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <p className="text-sm text-slate-400" data-testid="results-count">
            {t("catalog.resultsCount", { count: total })}
          </p>
          {isAuthenticated && selectedSet && (
            <button
              onClick={() => setScanModalOpen(true)}
              disabled={scanLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
                bg-cyan-600 hover:bg-cyan-500 text-white rounded-md transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="refresh-all-set-btn"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {t("catalog.refreshAllSet", { defaultValue: "Refresh All Set" })}
              <span className="ml-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold bg-amber-500/20 text-amber-400 rounded">
                {selectedSetCardCount}
              </span>
            </button>
          )}
          {scanFeedback && (
            <span className="text-sm text-green-400" data-testid="scan-feedback">
              {scanFeedback}
            </span>
          )}
          {scanError && (
            <span className="text-sm text-red-400" data-testid="scan-error">
              {scanError}
            </span>
          )}
        </div>
      )}

      {/* Credit confirm modal for Refresh All Set */}
      <CreditConfirmModal
        isOpen={scanModalOpen}
        onConfirm={handleRefreshAllSet}
        onCancel={() => setScanModalOpen(false)}
        cost={selectedSetCardCount}
        balance={balance ?? 0}
        actionLabel={t("catalog.refreshAllSetAction", {
          set: selectedSet,
          defaultValue: "Queue price updates for all cards in {{set}}",
        })}
        cardCount={selectedSetCardCount}
        bonusEligible={bonusEligible}
        onClaimBonus={async () => { await claimBonus(); }}
      />

      {/* Card grid */}
      {!loading && cards.length > 0 && (
        <>
          <div
            className={`grid ${GRID_SIZE_CONFIG[gridSize].gridClasses}`}
            data-testid="catalog-grid"
          >
            {cards.map((card) => (
              <CatalogCardTile key={card.id} card={card} ownedView={ownedView} compact={GRID_SIZE_CONFIG[gridSize].compact} />
            ))}
          </div>

          {/* Load more button */}
          {hasMore && (
            <div className="flex justify-center mt-8">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className={`px-6 py-2.5 rounded-lg font-medium transition-colors ${
                  loadingMore
                    ? "bg-slate-700 text-slate-500 cursor-wait"
                    : "bg-cyan-500 text-white hover:bg-cyan-600"
                }`}
                data-testid="load-more-btn"
              >
                {loadingMore ? t("common.loading") : t("catalog.loadMore")}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
