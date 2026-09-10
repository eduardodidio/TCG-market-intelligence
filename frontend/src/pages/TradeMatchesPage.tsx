import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import {
  fetchDuplicates,
  fetchTradeMatches,
  fetchReverseMatches,
} from "../api/tradeMatch";
import { Breadcrumb } from "../components/Breadcrumb";
import { DuplicatesList } from "../components/DuplicatesList";
import { EmptyState } from "../components/EmptyState";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { CardImage } from "../components/CardImage";
import { useRoutePrefix } from "../contexts/RoutePrefixContext";
import { scryfallImageByName } from "../utils/scryfall";
import type { DuplicateCard, TradeMatch, MatchedCard } from "../types/tradeMatch";

type Tab = "duplicates" | "theyHave" | "theyWant";

export function TradeMatchesPage() {
  const { t } = useTranslation();
  const prefix = useRoutePrefix();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("duplicates");

  const duplicatesFetcher = useCallback(
    () => fetchDuplicates({ limit: "200" }),
    [],
  );
  const matchesFetcher = useCallback(
    () => fetchTradeMatches(20),
    [],
  );
  const reverseFetcher = useCallback(
    () => fetchReverseMatches(20),
    [],
  );

  const { data: duplicates, loading: dupLoading } =
    useApi<DuplicateCard[]>(duplicatesFetcher, []);
  const { data: matches, loading: matchLoading } =
    useApi<TradeMatch[]>(matchesFetcher, []);
  const { data: reverseMatches, loading: reverseLoading } =
    useApi<TradeMatch[]>(reverseFetcher, []);

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-slate-400">
        {t("tradeMatch.loginRequired")}
      </div>
    );
  }

  const breadcrumbs = [
    { label: t("nav.dashboard"), to: `${prefix}/` },
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t("tradeMatch.title")}
        </h1>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-gray-200 dark:border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === tab.key
                ? "border-indigo-500 text-gray-900 dark:text-white"
                : "border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white"
            }`}
            data-testid={`tab-${tab.key}`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {/* Duplicates tab */}
      {activeTab === "duplicates" && (
        <DuplicatesTab
          duplicates={duplicates}
          loading={dupLoading}
        />
      )}

      {/* They Have What I Want tab */}
      {activeTab === "theyHave" && (
        <MatchesTab
          matches={matches}
          loading={matchLoading}
          emptyTitle={t("tradeMatch.noMatches")}
          emptyDescription={t("tradeMatch.noMatchesDesc")}
          emptyCta={{
            label: t("tradeMatch.goToWishlist"),
            onClick: () => navigate(`${prefix}/wishlist`),
          }}
        />
      )}

      {/* They Want What I Have tab */}
      {activeTab === "theyWant" && (
        <MatchesTab
          matches={reverseMatches}
          loading={reverseLoading}
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
}: {
  duplicates: DuplicateCard[] | null;
  loading: boolean;
}) {
  const { t } = useTranslation();

  if (loading) return <LoadingSpinner message={t("common.loading")} />;

  if (!duplicates || duplicates.length === 0) {
    return (
      <EmptyState
        title={t("tradeMatch.noDuplicates")}
        description={t("tradeMatch.noDuplicatesDesc")}
      />
    );
  }

  return <DuplicatesList duplicates={duplicates} />;
}

function MatchesTab({
  matches,
  loading,
  emptyTitle,
  emptyDescription,
  emptyCta,
}: {
  matches: TradeMatch[] | null;
  loading: boolean;
  emptyTitle: string;
  emptyDescription: string;
  emptyCta?: { label: string; onClick: () => void };
}) {
  const { t } = useTranslation();

  if (loading) return <LoadingSpinner message={t("common.loading")} />;

  if (!matches || matches.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        actions={emptyCta ? [emptyCta] : []}
      />
    );
  }

  return (
    <div className="space-y-4" data-testid="matches-list">
      {matches.map((match) => (
        <PartnerCard key={match.share_code} match={match} />
      ))}
    </div>
  );
}

function PartnerCard({ match }: { match: TradeMatch }) {
  const { t } = useTranslation();
  const prefix = useRoutePrefix();
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden"
      data-testid="partner-card"
    >
      {/* Partner header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-indigo-500 text-white text-sm font-bold">
            {match.partner_name[0]?.toUpperCase() ?? "?"}
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {match.partner_name}
            </p>
            <Link
              to={`${prefix}/marketplace`}
              className="text-xs text-indigo-500 dark:text-indigo-400 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {t("tradeMatch.viewCollection")}
            </Link>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
            {t("tradeMatch.matchingCards", {
              count: match.matching_card_count,
            })}
          </span>
          <svg
            className={`h-5 w-5 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}
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
        <div className="border-t border-gray-200 dark:border-slate-700 p-4">
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
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
  const prefix = useRoutePrefix();
  const imgSrc =
    card.image_uri ??
    (card.set_code
      ? scryfallImageByName(card.name_en, "small")
      : null);

  return (
    <Link
      to={`${prefix}/cards/${card.card_id}`}
      className="flex flex-col bg-gray-50 dark:bg-slate-700 rounded-md overflow-hidden no-underline"
      data-testid="matched-card"
    >
      <div className="aspect-[5/7] bg-gray-200 dark:bg-slate-600">
        <CardImage
          src={imgSrc}
          alt={card.name_en}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="p-1.5">
        <p className="text-xs font-medium text-gray-900 dark:text-white truncate">
          {card.name_en}
        </p>
        {card.set_code && (
          <p className="text-[10px] text-gray-500 dark:text-slate-400 uppercase">
            {card.set_code}
          </p>
        )}
      </div>
    </Link>
  );
}
