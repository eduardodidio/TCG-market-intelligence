import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { fetchCardLegalities } from "../api/banlist";
import { canonizeCard, fetchCollectionEntry, fetchCollectionHistory, refreshCardPrice } from "../api/collection";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl } from "../utils/scryfall";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
import { LegalityBadge } from "../components/LegalityBadge";
import type { CardLegality } from "../types/banlist";
import { ErrorBanner } from "../components/ErrorBanner";
import { PriceChart } from "../components/PriceChart";
import { SkeletonChartPanel, SkeletonInfoPanel } from "../components/Skeleton";
import type { CollectionCardDetail as CollectionCardDetailType } from "../types/api";

const RARITY_LABEL_KEYS: Record<string, string> = {
  M: "rarity.mythic",
  R: "rarity.rare",
  U: "rarity.uncommon",
  C: "rarity.common",
};

function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    myp: "MYP Cards",
  };
  return labels[source] ?? source;
}

export function CollectionCardDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const entryId = Number(id);

  const { currency } = useCurrency();
  const { getCardName, getSubtitleName } = useCardName();

  const detailFetcher = useCallback(
    () => fetchCollectionEntry(entryId, { currency }),
    [entryId, currency],
  );

  const { data: entry, loading, error, refetch, setData: setEntry } = useApi<CollectionCardDetailType>(
    detailFetcher,
    [entryId, currency],
  );

  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [canonizing, setCanonizing] = useState(false);

  const handleRefresh = useCallback(async () => {
    if (refreshing || !entry || entry.card_id == null) return;
    setRefreshing(true);
    setRefreshMsg(null);
    try {
      const params: Record<string, string> = {};
      if (currency !== "BRL") params.currency = currency;
      const res = await refreshCardPrice(entryId, Object.keys(params).length > 0 ? params : undefined);
      if (res.data) {
        setEntry(res.data);
        setRefreshMsg({ type: "success", text: t("collection.refreshSuccess") });
      } else {
        const msg = res.errors?.[0]?.message || t("collection.refreshError");
        setRefreshMsg({ type: "error", text: msg });
      }
    } catch {
      setRefreshMsg({ type: "error", text: t("collection.refreshError") });
    } finally {
      setRefreshing(false);
      setTimeout(() => setRefreshMsg(null), 3000);
    }
  }, [refreshing, entry, entryId, currency, t, setEntry]);

  const handleCanonize = useCallback(async () => {
    if (canonizing || !entry || entry.card_id != null) return;
    setCanonizing(true);
    setRefreshMsg(null);
    try {
      const params: Record<string, string> = {};
      if (currency !== "BRL") params.currency = currency;
      const res = await canonizeCard(entryId, Object.keys(params).length > 0 ? params : undefined);
      if (res.data) {
        setEntry(res.data);
        setRefreshMsg({ type: "success", text: t("collection.canonizeSuccess") });
      } else {
        const msg = res.errors?.[0]?.message || t("collection.canonizeError");
        setRefreshMsg({ type: "error", text: msg });
      }
    } catch {
      setRefreshMsg({ type: "error", text: t("collection.canonizeError") });
    } finally {
      setCanonizing(false);
      setTimeout(() => setRefreshMsg(null), 5000);
    }
  }, [canonizing, entry, entryId, currency, t, setEntry]);

  useEffect(() => {
    if (entry) {
      document.title = `${getCardName(entry.name_en, entry.name_pt, t("common.unknownCard"))} | TCG Market`;
    } else {
      document.title = `${t("collection.breadcrumbCollection")} | TCG Market`;
    }
  }, [entry]);

  if (loading) {
    return (
      <div data-testid="page-collection-detail">
        <div className="mb-6">
          <div className="animate-pulse bg-slate-700 rounded h-4 w-32" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonInfoPanel />
          <SkeletonChartPanel />
        </div>
      </div>
    );
  }

  if (error) {
    const is404 =
      error.toLowerCase().includes("not found") ||
      error.includes("HTTP_404") ||
      error.includes("404");

    if (is404) {
      return (
        <div data-testid="page-collection-detail">
          <div data-testid="entry-not-found" className="text-center py-12">
            <h2 className="text-2xl font-bold text-white mb-4">{t("collection.entryNotFound")}</h2>
            <p className="text-slate-400 mb-6">
              {t("collection.entryNotFoundMessage")}
            </p>
            <Link
              to="/collection"
              className="inline-block rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {t("collection.backToCollection")}
            </Link>
          </div>
        </div>
      );
    }

    return (
      <div data-testid="page-collection-detail">
        <ErrorBanner message={error} variant="full" onRetry={refetch} />
      </div>
    );
  }

  if (!entry) {
    return (
      <div data-testid="page-collection-detail">
        <div data-testid="entry-not-found" className="text-center py-12">
          <h2 className="text-2xl font-bold text-white mb-4">Collection entry not found</h2>
          <Link
            to="/collection"
            className="inline-block rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            Back to Collection
          </Link>
        </div>
      </div>
    );
  }

  const displayName = getCardName(entry.name_en, entry.name_pt, t("common.unknownCard"));
  const imageUrl = entry.image_url || scryfallImageUrl(entry.set_code, entry.collector_number);

  return (
    <div data-testid="page-collection-detail">
      {/* Breadcrumb */}
      <nav data-testid="breadcrumb" className="mb-6 text-sm text-slate-400" aria-label="Breadcrumb">
        <Link to="/collection" className="hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded">
          {t("collection.breadcrumbCollection")}
        </Link>
        <span className="mx-2" aria-hidden="true">&gt;</span>
        <span className="text-white">{displayName}</span>
      </nav>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left panel: Card info */}
        <div data-testid="card-info-panel" className="bg-slate-800 border border-slate-600 rounded-lg p-6">
          {/* Card image */}
          <div className="mb-6 flex justify-center">
            <img
              src={imageUrl}
              alt={displayName}
              data-testid="card-image"
              className="rounded-lg shadow-lg max-w-[250px] w-full"
              loading="eager"
              onError={(e) => { e.currentTarget.style.display = "none"; }}
            />
          </div>

          {/* Card name */}
          <h1 className="text-2xl font-bold text-white mb-1">{displayName}</h1>
          {(() => {
            const subtitle = getSubtitleName(entry.name_en, entry.name_pt, t("common.unknownCard"));
            return subtitle ? (
              <p className="text-sm text-slate-400 mb-4" data-testid="name-pt">{subtitle}</p>
            ) : null;
          })()}

          {/* Set and collector number */}
          <div className="flex items-center gap-3 mb-4">
            {entry.set_code && (
              <span className="rounded bg-slate-700 px-2 py-1 text-xs font-mono text-slate-400" data-testid="set-code">
                {entry.set_code}
              </span>
            )}
            {entry.collector_number && (
              <span className="text-sm text-slate-400" data-testid="collector-number">
                #{entry.collector_number}
              </span>
            )}
          </div>

          {/* Collection metadata */}
          <div className="mb-6" data-testid="collection-metadata">
            <p className="text-sm text-slate-400 mb-2">{t("collection.collectionInfo")}</p>
            <div className="flex flex-wrap gap-2">
              {entry.quantity > 1 && (
                <span className="inline-block rounded-full bg-indigo-500 px-3 py-1 text-xs font-bold text-white" data-testid="quantity-badge">
                  x{entry.quantity}
                </span>
              )}
              {entry.quality && (
                <span className="inline-block rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-400" data-testid="quality-badge">
                  {entry.quality}
                </span>
              )}
              {entry.language && (
                <span className="inline-block rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-400" data-testid="language-badge">
                  {entry.language}
                </span>
              )}
              {entry.rarity && (
                <span className="inline-block rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-400" data-testid="rarity-badge">
                  {RARITY_LABEL_KEYS[entry.rarity] ? t(RARITY_LABEL_KEYS[entry.rarity]) : entry.rarity}
                </span>
              )}
              {entry.extras && (
                <span className="inline-block rounded-full bg-amber-600/90 px-3 py-1 text-xs font-bold text-white" data-testid="extras-badge">
                  {entry.extras}
                </span>
              )}
            </div>
          </div>

          {/* Latest price */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-sm text-slate-400">{t("cardDetail.latestPrice")}</p>
              {entry.card_id != null && (
                <button
                  data-testid="refresh-price-btn"
                  onClick={handleRefresh}
                  disabled={refreshing}
                  title={refreshing ? t("collection.refreshing") : t("collection.refresh")}
                  className="w-8 h-8 flex items-center justify-center rounded-full bg-slate-700 hover:bg-slate-600 text-slate-400 hover:text-cyan-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  <svg
                    className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
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
            <p data-testid="latest-price" className="text-3xl font-bold text-white flex items-center gap-2">
              <CurrencyIndicator currency={currency} size={24} />
              {formatCurrency(entry.latest_price, currency)}
            </p>
            {refreshMsg && (
              <p
                data-testid="refresh-message"
                className={`text-xs mt-1 ${refreshMsg.type === "success" ? "text-green-400" : "text-red-400"}`}
              >
                {refreshMsg.text}
              </p>
            )}
          </div>

          {/* Linked status */}
          {entry.card_id == null && (
            <div className="mb-6 rounded-md bg-slate-700/50 p-4" data-testid="unlinked-notice">
              <p className="text-sm text-amber-400">
                {t("collection.notLinked")}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {t("collection.notLinkedDescription")}
              </p>
              <button
                data-testid="canonize-btn"
                onClick={handleCanonize}
                disabled={canonizing}
                className="mt-3 inline-flex items-center gap-2 rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                {canonizing ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {t("collection.canonizing")}
                  </>
                ) : (
                  t("collection.canonize")
                )}
              </button>
            </div>
          )}

          {/* Source links */}
          {entry.source_cards.length > 0 && (
            <div className="mb-6">
              <p className="text-sm text-slate-400 mb-2">{t("cardDetail.sources")}</p>
              <div className="flex flex-wrap gap-2">
                {entry.source_cards.map((sc) => (
                  <a
                    key={sc.external_id}
                    href={sc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="source-link"
                    className="inline-flex items-center gap-1 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                  >
                    {sourceLabel(sc.source)}
                    <svg
                      className="h-3 w-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      />
                    </svg>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* External Links */}
          <div className="mt-6" data-testid="external-links">
            <p className="text-sm text-slate-400 mb-2">{t("cardDetail.externalLinks")}</p>
            <div className="flex flex-wrap gap-2">
              {entry.scryfall_url && (
                <a
                  href={entry.scryfall_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="scryfall-link"
                  className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  {t("cardDetail.viewOnScryfall")}
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
              {entry.ligamagic_url && (
                <a
                  href={entry.ligamagic_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="ligamagic-link"
                  className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  {t("cardDetail.viewOnLigaMagic")}
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Right panel: Price chart */}
        <div>
          {entry.card_id != null ? (
            <PriceChart
              cardId={entry.card_id}
              currency={currency}
              fetchHistory={(period, curr) =>
                fetchCollectionHistory(entryId, period, curr)
              }
            />
          ) : (
            <div data-testid="no-price-chart" className="bg-slate-800 border border-slate-600 rounded-lg p-8 text-center">
              <p className="text-slate-400">
                {t("collection.noPriceChart")}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Legality section */}
      <LegalitySection cardId={entry.card_id} />
    </div>
  );
}

const DEFAULT_SHOWN = 6;

function LegalitySection({ cardId }: { cardId: number | null }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const legalitiesFetcher = useCallback(
    () => {
      if (cardId == null) {
        return Promise.resolve({
          data: [] as CardLegality[],
          meta: { cursor: null, total: null, offset: null, request_id: "" },
          errors: [],
        });
      }
      return fetchCardLegalities(cardId);
    },
    [cardId],
  );

  const { data: legalities, loading } = useApi<CardLegality[]>(
    legalitiesFetcher,
    [cardId],
  );

  if (cardId == null) {
    return (
      <div
        data-testid="legality-section"
        className="mt-6 bg-slate-800 border border-slate-600 rounded-lg p-6"
      >
        <h2 className="text-lg font-bold text-white mb-3">
          {t("legality.title")}
        </h2>
        <p className="text-sm text-slate-400">
          {t("legality.unavailable")}
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div
        data-testid="legality-section"
        className="mt-6 bg-slate-800 border border-slate-600 rounded-lg p-6"
      >
        <h2 className="text-lg font-bold text-white mb-3">
          {t("legality.title")}
        </h2>
        <div className="animate-pulse flex gap-2 flex-wrap">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-7 w-28 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!legalities || legalities.length === 0) {
    return null;
  }

  // Sort: banned/restricted first, then legal, then not_legal
  const statusOrder: Record<string, number> = {
    banned: 0,
    restricted: 1,
    legal: 2,
    not_legal: 3,
  };
  const sorted = [...legalities].sort(
    (a, b) => (statusOrder[a.status] ?? 4) - (statusOrder[b.status] ?? 4),
  );

  const shown = expanded ? sorted : sorted.slice(0, DEFAULT_SHOWN);
  const hasMore = sorted.length > DEFAULT_SHOWN;

  return (
    <div
      data-testid="legality-section"
      className="mt-6 bg-slate-800 border border-slate-600 rounded-lg p-6"
    >
      <h2 className="text-lg font-bold text-white mb-3">
        {t("legality.title")}
      </h2>
      <div className="flex flex-wrap gap-2">
        {shown.map((leg) => (
          <LegalityBadge
            key={leg.format}
            format={leg.format}
            status={leg.status}
            size="md"
          />
        ))}
      </div>
      {hasMore && (
        <button
          data-testid="legality-expand"
          onClick={() => setExpanded(!expanded)}
          className="mt-3 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {expanded ? t("banlist.show_less") : t("banlist.show_all")}
        </button>
      )}
    </div>
  );
}
