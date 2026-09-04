import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { Breadcrumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { SearchBar } from "../components/SearchBar";
import { SkeletonCard } from "../components/Skeleton";
import { useCatalogCards } from "../hooks/useCatalogCards";
import type { CatalogCard } from "../hooks/useCatalogCards";
import { useCatalogSets } from "../hooks/useCatalogSets";
import { useCatalogStats } from "../hooks/useCatalogStats";
import { useCardName } from "../hooks/useCardName";

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

function CatalogCardTile({ card }: { card: CatalogCard }) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();
  const displayName = getCardName(card.name_en, card.name_pt, t("common.unknownCard"));

  return (
    <Link
      to={`/cards/${card.id}`}
      className="group block bg-slate-800 rounded-lg overflow-hidden
        border border-slate-600 hover:border-cyan-400/50
        transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
      data-testid={`catalog-card-${card.id}`}
    >
      {/* Card image */}
      <div
        className="aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800
          flex items-center justify-center overflow-hidden"
      >
        {card.image_uri ? (
          <img
            src={card.image_uri}
            alt={displayName}
            className="w-full h-full object-cover"
            loading="lazy"
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
            <span className="inline-block px-1.5 py-0.5 text-xs font-mono bg-slate-700 text-slate-400 rounded">
              {card.set_code}
            </span>
          )}
          <RarityBadge rarity={card.rarity} />
        </div>

        {card.liga_price != null ? (
          <p className="mt-2 text-sm font-bold text-cyan-400" data-testid="card-price">
            R$ {card.liga_price.toFixed(2)}
          </p>
        ) : (
          <p className="mt-2 text-sm text-slate-500" data-testid="card-price">
            {t("common.noPriceData")}
          </p>
        )}
      </div>
    </Link>
  );
}

export function CatalogPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    document.title = `${t("catalog.title")} | TCG Market`;
  }, [t]);

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
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Sync filters to URL search params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (searchTerm) params.name = searchTerm;
    if (selectedSet) params.set_code = selectedSet;
    if (selectedRarities.size > 0) params.rarity = [...selectedRarities].join(",");
    if (selectedColors.size > 0) params.color = [...selectedColors].join(",");
    if (hasPrice) params.has_price = hasPrice;
    setSearchParams(params, { replace: true });
  }, [searchTerm, selectedSet, selectedRarities, selectedColors, hasPrice, setSearchParams]);

  const filters = {
    name: searchTerm,
    set_code: selectedSet,
    rarity: [...selectedRarities].join(","),
    color: [...selectedColors].join(","),
    has_price: hasPrice,
    min_price: "",
    max_price: "",
    sort_by: "name",
    sort_dir: "asc",
  };

  const { cards, total, loading, loadingMore, error, hasMore, loadMore } = useCatalogCards(filters);
  const { sets } = useCatalogSets();
  const { stats } = useCatalogStats();

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

      {/* Search and filters */}
      <div className="space-y-4 mb-6">
        <div className="flex gap-3 items-center">
          <div className="flex-1">
            <SearchBar
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder={t("catalog.searchPlaceholder")}
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

      {/* Error state */}
      {error && (
        <div className="mb-6">
          <ErrorBanner message={error} variant="inline" />
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4"
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
              ? t("catalog.emptyFiltered")
              : t("catalog.emptyDescription")
          }
          action={
            hasActiveFilters
              ? { label: t("common.clearFilters"), onClick: handleClearFilters }
              : undefined
          }
        />
      )}

      {/* Results count */}
      {!loading && cards.length > 0 && (
        <p className="text-sm text-slate-400 mb-4" data-testid="results-count">
          {t("catalog.resultsCount", { count: total })}
        </p>
      )}

      {/* Card grid */}
      {!loading && cards.length > 0 && (
        <>
          <div
            className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4"
            data-testid="catalog-grid"
          >
            {cards.map((card) => (
              <CatalogCardTile key={card.id} card={card} />
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
