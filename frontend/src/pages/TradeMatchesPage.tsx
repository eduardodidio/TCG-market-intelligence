import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import { useCardListFilters } from "../hooks/useCardListFilters";
import { useGridSize } from "../hooks/useGridSize";
import {
  fetchDuplicates,
  fetchDuplicateSets,
  fetchTradeMatches,
  fetchReverseMatches,
} from "../api/tradeMatch";
import { Breadcrumb } from "../components/Breadcrumb";
import { CardFilterBar } from "../components/CardFilterBar";
import { DuplicatesList } from "../components/DuplicatesList";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { SkeletonCard } from "../components/Skeleton";
import { CardImage } from "../components/CardImage";
import { scryfallImageByName } from "../utils/scryfall";
import { filterCardList, buildSetOptions } from "../utils/cardListFilter";
import { DUPLICATES_SORT_OPTIONS, MATCH_SORT_OPTIONS } from "../utils/tradeSortOptions";
import { GRID_SIZE_CONFIG, type GridSize } from "../utils/constants";
import type { DuplicateCard, TradeMatch, MatchedCard } from "../types/tradeMatch";

type Tab = "duplicates" | "theyHave" | "theyWant";

const DUPLICATES_DEFAULT_SORT = { sortBy: "quantity", sortDir: "desc" as const };
const MATCHES_DEFAULT_SORT = { sortBy: "name", sortDir: "asc" as const };

export function TradeMatchesPage() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("duplicates");

  const filters = useCardListFilters({
    defaultSortBy: DUPLICATES_DEFAULT_SORT.sortBy,
    defaultSortDir: DUPLICATES_DEFAULT_SORT.sortDir,
  });
  const { gridSize, setGridSize } = useGridSize();

  const handleTabChange = useCallback(
    (tab: Tab) => {
      setActiveTab(tab);
      const defaults = tab === "duplicates" ? DUPLICATES_DEFAULT_SORT : MATCHES_DEFAULT_SORT;
      filters.setSort(defaults.sortBy, defaults.sortDir);
    },
    [filters],
  );

  const duplicatesFetcher = useCallback(
    () =>
      fetchDuplicates({
        limit: "200",
        search: filters.debouncedSearch,
        set_code: filters.selectedSet ?? "",
        sort_by: filters.sortBy,
        sort_dir: filters.sortDir,
      }),
    [filters.debouncedSearch, filters.selectedSet, filters.sortBy, filters.sortDir],
  );
  const duplicateSetsFetcher = useCallback(() => fetchDuplicateSets(), []);
  const matchesFetcher = useCallback(() => fetchTradeMatches(20), []);
  const reverseFetcher = useCallback(() => fetchReverseMatches(20), []);

  const {
    data: duplicates,
    loading: dupLoading,
    error: dupError,
    refetch: refetchDuplicates,
  } = useApi<DuplicateCard[]>(duplicatesFetcher, [duplicatesFetcher]);
  const { data: duplicateSets } = useApi(duplicateSetsFetcher, []);
  const {
    data: matches,
    loading: matchLoading,
    error: matchError,
    refetch: refetchMatches,
  } = useApi<TradeMatch[]>(matchesFetcher, []);
  const {
    data: reverseMatches,
    loading: reverseLoading,
    error: reverseError,
    refetch: refetchReverse,
  } = useApi<TradeMatch[]>(reverseFetcher, []);

  const duplicateSetOptions = useMemo(
    () =>
      (duplicateSets ?? [])
        .filter((s) => s.set_code)
        .map((s) => ({
          label: s.set_name || s.set_code!.toUpperCase(),
          value: s.set_code!.toLowerCase(),
        })),
    [duplicateSets],
  );

  const allMatchedCards = useMemo(() => {
    const source = activeTab === "theyWant" ? reverseMatches : matches;
    return (source ?? []).flatMap((m) => m.matched_cards);
  }, [activeTab, matches, reverseMatches]);

  const matchSetOptions = useMemo(
    () =>
      buildSetOptions(allMatchedCards, {
        name: (c: MatchedCard) => c.name_en,
        setCode: (c: MatchedCard) => c.set_code,
      }),
    [allMatchedCards],
  );

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12 text-slate-400">
        {t("tradeMatch.loginRequired")}
      </div>
    );
  }

  const breadcrumbs = [
    { label: t("nav.dashboard"), to: "/" },
    { label: t("tradeMatch.title") },
  ];

  const tabs: { key: Tab; labelKey: string }[] = [
    { key: "duplicates", labelKey: "tradeMatch.duplicates" },
    { key: "theyHave", labelKey: "tradeMatch.theyHave" },
    { key: "theyWant", labelKey: "tradeMatch.theyWant" },
  ];

  return (
    <div>
      <Breadcrumb items={breadcrumbs} />

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">{t("tradeMatch.title")}</h1>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => handleTabChange(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === tab.key
                ? "border-indigo-500 text-white"
                : "border-transparent text-slate-400 hover:text-white"
            }`}
            data-testid={`tab-${tab.key}`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      <CardFilterBar
        search={filters.search}
        onSearchChange={filters.setSearch}
        searchPlaceholder={t("tradeFilters.searchPlaceholder")}
        sortOptions={activeTab === "duplicates" ? DUPLICATES_SORT_OPTIONS : MATCH_SORT_OPTIONS}
        sortValue={filters.sortValue}
        onSortChange={filters.setSort}
        setOptions={activeTab === "duplicates" ? duplicateSetOptions : matchSetOptions}
        selectedSet={filters.selectedSet}
        onSetSelect={filters.setSelectedSet}
        gridSize={gridSize}
        onGridSizeChange={setGridSize}
      />

      {/* Duplicates tab */}
      {activeTab === "duplicates" && (
        <DuplicatesTab
          duplicates={duplicates}
          loading={dupLoading}
          error={dupError}
          onRetry={refetchDuplicates}
          gridClasses={GRID_SIZE_CONFIG[gridSize].gridClasses}
        />
      )}

      {/* They Have What I Want tab */}
      {activeTab === "theyHave" && (
        <MatchesTab
          matches={matches}
          loading={matchLoading}
          error={matchError}
          onRetry={refetchMatches}
          search={filters.debouncedSearch}
          selectedSet={filters.selectedSet}
          gridSize={gridSize}
          emptyTitle={t("tradeMatch.noMatches")}
          emptyDescription={t("tradeMatch.noMatchesDesc")}
          emptyCta={{
            label: t("tradeMatch.goToWishlist"),
            onClick: () => navigate("/wishlist"),
          }}
        />
      )}

      {/* They Want What I Have tab */}
      {activeTab === "theyWant" && (
        <MatchesTab
          matches={reverseMatches}
          loading={reverseLoading}
          error={reverseError}
          onRetry={refetchReverse}
          search={filters.debouncedSearch}
          selectedSet={filters.selectedSet}
          gridSize={gridSize}
          emptyTitle={t("tradeMatch.noReverseMatches")}
          emptyDescription={t("tradeMatch.shareToMatch")}
        />
      )}
    </div>
  );
}

function DuplicatesTab({
  duplicates,
  loading,
  error,
  onRetry,
  gridClasses,
}: {
  duplicates: DuplicateCard[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  gridClasses: string;
}) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={`grid ${gridClasses}`}>
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={onRetry} />;
  }

  if (!duplicates || duplicates.length === 0) {
    return (
      <EmptyState
        title={t("tradeMatch.noDuplicates")}
        description={t("tradeMatch.noDuplicatesDesc")}
      />
    );
  }

  return <DuplicatesList duplicates={duplicates} gridClasses={gridClasses} />;
}

function MatchesTab({
  matches,
  loading,
  error,
  onRetry,
  search,
  selectedSet,
  gridSize,
  emptyTitle,
  emptyDescription,
  emptyCta,
}: {
  matches: TradeMatch[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  search: string;
  selectedSet: string | null;
  gridSize: GridSize;
  emptyTitle: string;
  emptyDescription: string;
  emptyCta?: { label: string; onClick: () => void };
}) {
  const { t } = useTranslation();

  const filteredMatches = useMemo(() => {
    if (!matches) return [];
    return matches
      .map((match) => ({
        ...match,
        matched_cards: filterCardList(
          match.matched_cards,
          { search, set: selectedSet },
          {
            name: (c: MatchedCard) => c.name_en,
            setCode: (c: MatchedCard) => c.set_code,
          },
        ),
      }))
      .filter((match) => match.matched_cards.length > 0);
  }, [matches, search, selectedSet]);

  if (loading) {
    return (
      <div className={`grid ${GRID_SIZE_CONFIG[gridSize].gridClasses}`}>
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={onRetry} />;
  }

  if (!matches || matches.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        actions={emptyCta ? [emptyCta] : []}
      />
    );
  }

  if (filteredMatches.length === 0) {
    return <EmptyState title={t("tradeFilters.noResults")} />;
  }

  return (
    <div className="space-y-4" data-testid="matches-list">
      {filteredMatches.map((match) => (
        <PartnerCard key={match.share_code} match={match} gridClasses={GRID_SIZE_CONFIG[gridSize].gridClasses} />
      ))}
    </div>
  );
}

function PartnerCard({ match, gridClasses }: { match: TradeMatch; gridClasses: string }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden"
      data-testid="partner-card"
    >
      {/* Partner header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-indigo-500 text-white text-sm font-bold">
            {match.partner_name[0]?.toUpperCase() ?? "?"}
          </div>
          <div>
            <p className="text-sm font-medium text-white">{match.partner_name}</p>
            <Link
              to={"/marketplace"}
              className="text-xs text-indigo-400 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {t("tradeMatch.viewCollection")}
            </Link>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-900/50 text-indigo-300">
            {t("tradeMatch.matchingCards", {
              count: match.matched_cards.length,
            })}
          </span>
          <svg
            className={`h-5 w-5 text-slate-400 transition-transform ${expanded ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>

      {/* Matched cards (expandable) */}
      {expanded && (
        <div className="border-t border-slate-700 p-4">
          <div className={`grid ${gridClasses}`}>
            {match.matched_cards.map((card) => (
              <MatchedCardThumbnail key={card.card_id} card={card} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MatchedCardThumbnail({ card }: { card: MatchedCard }) {
  const imgSrc =
    card.image_uri ??
    (card.set_code
      ? scryfallImageByName(card.name_en, "small")
      : null);

  return (
    <Link
      to={`/cards/${card.card_id}`}
      className="flex flex-col bg-slate-700 rounded-md overflow-hidden no-underline"
      data-testid="matched-card"
    >
      <div className="aspect-[5/7] bg-slate-600">
        <CardImage
          src={imgSrc}
          alt={card.name_en}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="p-1.5">
        <p className="text-xs font-medium text-white truncate">{card.name_en}</p>
        {card.set_code && (
          <p className="text-[10px] text-slate-400 uppercase">{card.set_code}</p>
        )}
      </div>
    </Link>
  );
}
