import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useCredits } from "../hooks/useCredits";
import { canonizeCard, deleteCollectionEntry, fetchCollectionEntry, fetchCollectionHistory, patchCollectionEntry, refreshCardPrice, refreshCardPriceLiga } from "../api/collection";
import { fetchCardBanHistory } from "../api/banlist";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl } from "../utils/scryfall";
import { Breadcrumb } from "../components/Breadcrumb";
import { BanEventCard } from "../components/BanEventCard";
import { CreditConfirmModal } from "../components/CreditConfirmModal";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
import { DeleteEntryButton } from "../components/DeleteEntryButton";
import { InlineEditField } from "../components/InlineEditField";
import { LegalityPanel } from "../components/LegalityPanel";
import { ErrorBanner } from "../components/ErrorBanner";
import { ManualPriceInput } from "../components/ManualPriceInput";
import { MetricsPanel } from "../components/MetricsPanel";
import { PriceChart } from "../components/PriceChart";
import { FoilBadge } from "../components/FoilBadge";
import { PriceSourceBadge } from "../components/PriceSourceBadge";
import { QuantityStepper } from "../components/QuantityStepper";
import { SkeletonChartPanel, SkeletonInfoPanel } from "../components/Skeleton";
import type { CardBanHistoryEntry } from "../types/banlist";
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
    liga: "LigaMagic",
  };
  return labels[source] ?? source;
}

const QUALITY_OPTIONS = [
  { label: "M", value: "M" },
  { label: "NM", value: "NM" },
  { label: "SP", value: "SP" },
  { label: "MP", value: "MP" },
  { label: "HP", value: "HP" },
  { label: "D", value: "D" },
];

const LANGUAGE_OPTIONS = [
  { label: "BR", value: "BR" },
  { label: "EN", value: "EN" },
  { label: "DE", value: "DE" },
  { label: "ES", value: "ES" },
  { label: "FR", value: "FR" },
  { label: "IT", value: "IT" },
  { label: "JP", value: "JP" },
  { label: "KO", value: "KO" },
  { label: "RU", value: "RU" },
  { label: "TW", value: "TW" },
];

export function CollectionCardDetail() {
  const { t } = useTranslation();
  const navigate = useNavigate();
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
    { refetchOnFocus: true },
  );

  const [period, setPeriod] = useState("30d");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshingLiga, setRefreshingLiga] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<{ type: "success" | "error" | "warning"; text: string } | null>(null);
  const [canonizing, setCanonizing] = useState(false);
  const [creditModalOpen, setCreditModalOpen] = useState(false);
  const [creditModalTarget, setCreditModalTarget] = useState<"liga" | "myp">("liga");
  const { balance, isAdmin, refetch: refetchCredits } = useCredits();

  // Refetch credit balance when navigating between cards
  useEffect(() => {
    refetchCredits();
  }, [entryId]); // eslint-disable-line react-hooks/exhaustive-deps

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
        setRefreshMsg({ type: "error", text: `${msg}. ${t("collection.refreshFallbackHint")}` });
      }
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 402) {
        refetchCredits();
        setRefreshMsg({ type: "error", text: t("credits.insufficient") });
      } else {
        setRefreshMsg({ type: "error", text: `${t("collection.refreshError")}. ${t("collection.refreshFallbackHint")}` });
      }
    } finally {
      setRefreshing(false);
      setTimeout(() => setRefreshMsg(null), 3000);
    }
  }, [refreshing, entry, entryId, currency, t, setEntry, refetchCredits]);

  const handleRefreshLiga = useCallback(async () => {
    if (refreshingLiga || !entry) return;
    const hasName = !!(entry.name_en || entry.name_pt);
    if (!hasName) return;
    setRefreshingLiga(true);
    setRefreshMsg(null);
    try {
      const params: Record<string, string> = {};
      if (currency !== "BRL") params.currency = currency;
      const res = await refreshCardPriceLiga(entryId, Object.keys(params).length > 0 ? params : undefined);
      if (res.data) {
        setEntry(res.data);
        if (res.errors && res.errors.length > 0) {
          const errMsg = res.errors[0].message;
          const hint = res.errors[0].code === "liga_warning" ? ` ${t("collection.ligaErrorHint")}` : "";
          setRefreshMsg({ type: "warning", text: `${errMsg}.${hint}` });
        } else {
          setRefreshMsg({ type: "success", text: t("collection.refreshLigaSuccess") });
        }
      } else {
        const msg = res.errors?.[0]?.message || t("collection.refreshLigaError");
        setRefreshMsg({ type: "error", text: msg });
      }
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 402) {
        refetchCredits();
        setRefreshMsg({ type: "error", text: t("credits.insufficient") });
      } else {
        setRefreshMsg({ type: "error", text: t("collection.refreshLigaError") });
      }
    } finally {
      setRefreshingLiga(false);
      setTimeout(() => setRefreshMsg(null), 5000);
    }
  }, [refreshingLiga, entry, entryId, currency, t, setEntry, refetchCredits]);

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
        if (res.errors && res.errors.length > 0) {
          // Partial success: card linked but MYP fetch failed
          setRefreshMsg({ type: "warning", text: t("collection.canonizePartial") });
        } else {
          setRefreshMsg({ type: "success", text: t("collection.canonizeSuccess") });
        }
      } else {
        const msg = res.errors?.[0]?.message || t("collection.canonizeError");
        setRefreshMsg({ type: "error", text: msg });
        refetch();
      }
    } catch {
      setRefreshMsg({ type: "error", text: t("collection.canonizeError") });
      refetch();
    } finally {
      setCanonizing(false);
      setTimeout(() => setRefreshMsg(null), 5000);
    }
  }, [canonizing, entry, entryId, currency, t, setEntry, refetch]);

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
          <h2 className="text-2xl font-bold text-white mb-4">{t("collection.entryNotFound")}</h2>
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

  const displayName = getCardName(entry.name_en, entry.name_pt, t("common.unknownCard"));
  const imageUrl = entry.image_url || scryfallImageUrl(entry.set_code, entry.collector_number);

  return (
    <div data-testid="page-collection-detail">
      <Breadcrumb
        items={[
          { label: t("collection.breadcrumbCollection"), to: "/collection" },
          { label: displayName },
        ]}
      />

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
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-white">{displayName}</h1>
            {entry.is_foil && <FoilBadge variant="full" />}
          </div>
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

          {/* Collection metadata — editable */}
          <div className="mb-6" data-testid="collection-metadata">
            <p className="text-sm text-slate-400 mb-3">{t("collection.collectionInfo")}</p>
            <div className="space-y-3">
              {/* Quantity — stepper */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 uppercase tracking-wider">{t("inlineEdit.quantityLabel")}</span>
                <QuantityStepper
                  value={entry.quantity}
                  onChange={async (newQty) => {
                    const res = await patchCollectionEntry(entryId, { quantity: newQty });
                    if (res.data) {
                      setEntry({ ...entry, quantity: res.data.quantity });
                    }
                  }}
                />
              </div>

              {/* Quality — select */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 uppercase tracking-wider">{t("inlineEdit.qualityLabel")}</span>
                <InlineEditField
                  label="quality"
                  type="select"
                  options={QUALITY_OPTIONS}
                  value={entry.quality || "NM"}
                  onSave={async (val) => {
                    const res = await patchCollectionEntry(entryId, { quality: val });
                    if (res.data) {
                      setEntry({ ...entry, quality: res.data.quality });
                    } else {
                      throw new Error("save failed");
                    }
                  }}
                />
              </div>

              {/* Language — select */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 uppercase tracking-wider">{t("inlineEdit.languageLabel")}</span>
                <InlineEditField
                  label="language"
                  type="select"
                  options={LANGUAGE_OPTIONS}
                  value={entry.language || "EN"}
                  onSave={async (val) => {
                    const res = await patchCollectionEntry(entryId, { language: val });
                    if (res.data) {
                      setEntry({ ...entry, language: res.data.language });
                    } else {
                      throw new Error("save failed");
                    }
                  }}
                />
              </div>

              {/* Extras — text */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 uppercase tracking-wider">{t("inlineEdit.extrasLabel")}</span>
                <InlineEditField
                  label="extras"
                  type="text"
                  value={entry.extras || ""}
                  onSave={async (val) => {
                    const res = await patchCollectionEntry(entryId, { extras: val });
                    if (res.data) {
                      setEntry({ ...entry, extras: res.data.extras });
                    } else {
                      throw new Error("save failed");
                    }
                  }}
                />
              </div>

              {/* Rarity — read-only */}
              {entry.rarity && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500 uppercase tracking-wider">{t("cardDetail.rarity")}</span>
                  <span className="inline-block rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-400" data-testid="rarity-badge">
                    {RARITY_LABEL_KEYS[entry.rarity] ? t(RARITY_LABEL_KEYS[entry.rarity]) : entry.rarity}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Latest price */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-sm text-slate-400">{entry.is_foil ? t("card.foilPrice") : t("cardDetail.latestPrice")}</p>
              <PriceSourceBadge priceSource={entry.price_source} />
            </div>
            {/* Refresh button hierarchy: Liga primary, MYP secondary */}
            <div className="flex items-center gap-2 mb-2" data-testid="refresh-buttons">
              {!!(entry.name_en || entry.name_pt) && (
                <button
                  data-testid="refresh-liga-btn"
                  onClick={() => { setCreditModalTarget("liga"); setCreditModalOpen(true); }}
                  disabled={refreshingLiga}
                  title={t("collection.refreshLigaTooltip")}
                  className="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 px-3 py-1.5 text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  <svg
                    className={`h-4 w-4 ${refreshingLiga ? "animate-spin" : ""}`}
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
                  {t("card.refreshLiga")}
                </button>
              )}
              {entry.card_id != null && (
                <button
                  data-testid="refresh-price-btn"
                  onClick={() => { setCreditModalTarget("myp"); setCreditModalOpen(true); }}
                  disabled={refreshing}
                  title={refreshing ? t("collection.refreshing") : t("collection.refresh")}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-500 bg-transparent hover:bg-slate-700 px-2.5 py-1 text-xs font-medium text-slate-400 hover:text-slate-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
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
                  {t("card.refreshMyp")}
                </button>
              )}
            </div>
            <p data-testid="latest-price" className="text-3xl font-bold text-white flex items-center gap-2">
              <CurrencyIndicator currency={currency} size={24} />
              {formatCurrency(entry.latest_price, currency)}
            </p>
            {entry.quantity > 1 && entry.latest_price != null && (
              <p className="text-sm text-slate-400 mt-1 flex items-center gap-1" data-testid="line-total">
                <CurrencyIndicator currency={currency} size={14} />
                {formatCurrency(entry.latest_price, currency)}
                {" "}
                {t("collection.lineTotal", {
                  qty: entry.quantity,
                  total: formatCurrency(entry.latest_price * entry.quantity, currency),
                })}
              </p>
            )}
            {refreshMsg && (
              <p
                data-testid="refresh-message"
                className={`text-xs mt-1 ${refreshMsg.type === "success" ? "text-green-400" : refreshMsg.type === "warning" ? "text-amber-400" : "text-red-400"}`}
              >
                {refreshMsg.text}
              </p>
            )}
            <ManualPriceInput entryId={entryId} currency={currency} onSaved={refetch} />
          </div>

          {/* Linked status — show canonize when unlinked OR linked but no source cards */}
          {(entry.card_id == null || entry.source_cards.length === 0) && (
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

          {/* Delete entry */}
          <div className="mt-6 mb-6" data-testid="delete-section">
            <DeleteEntryButton
              entryName={displayName}
              onConfirm={async () => {
                await deleteCollectionEntry(entryId);
                navigate("/collection");
              }}
            />
          </div>

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

        {/* Right panel: Price chart + Metrics */}
        <div>
          {entry.card_id != null ? (
            <>
              <PriceChart
                cardId={entry.card_id}
                currency={currency}
                period={period}
                onPeriodChange={setPeriod}
                fetchHistory={(p, curr) =>
                  fetchCollectionHistory(entryId, p, curr)
                }
              />
              <div className="mt-4">
                <MetricsPanel
                  entryId={entryId}
                  period={period}
                  currency={currency}
                />
              </div>
            </>
          ) : (
            <div data-testid="no-price-chart" className="bg-slate-800 border border-slate-600 rounded-lg p-8 text-center">
              <p className="text-slate-400">
                {t("collection.noPriceChart")}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Format Legality */}
      <div className="mt-6">
        <LegalityPanel entryId={entryId} cardId={entry.card_id} />
      </div>

      {/* Ban History */}
      {entry.card_id != null && (
        <BanHistorySection cardId={entry.card_id} />
      )}

      <CreditConfirmModal
        isOpen={creditModalOpen}
        onCancel={() => setCreditModalOpen(false)}
        onConfirm={() => {
          setCreditModalOpen(false);
          if (creditModalTarget === "liga") {
            handleRefreshLiga();
          } else {
            handleRefresh();
          }
        }}
        cost={1}
        balance={balance ?? 0}
        actionLabel={t("credits.refreshCost")}
        isAdmin={isAdmin}
      />
    </div>
  );
}

function BanHistorySection({ cardId }: { cardId: number }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [history, setHistory] = useState<CardBanHistoryEntry[] | null>(null);
  const [loading, setLoading] = useState(false);

  const handleToggle = useCallback(async () => {
    const willExpand = !expanded;
    setExpanded(willExpand);

    if (willExpand && history === null) {
      setLoading(true);
      try {
        const res = await fetchCardBanHistory(cardId);
        setHistory(res.data ?? []);
      } catch {
        setHistory([]);
      } finally {
        setLoading(false);
      }
    }
  }, [expanded, history, cardId]);

  return (
    <div
      data-testid="ban-history-section"
      className="mt-6 bg-slate-800 border border-slate-600 rounded-lg p-6"
    >
      <button
        data-testid="ban-history-toggle"
        onClick={handleToggle}
        className="flex items-center gap-2 w-full text-left"
      >
        <svg
          className={`h-5 w-5 text-slate-400 transition-transform ${
            expanded ? "rotate-90" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
        <svg
          className="h-5 w-5 text-slate-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h2 className="text-lg font-bold text-white">
          {t("banHistory.title")}
        </h2>
      </button>

      {expanded && (
        <div className="mt-4" data-testid="ban-history-content">
          {loading ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div
                  key={i}
                  className="animate-pulse bg-slate-700 rounded-lg h-16"
                />
              ))}
            </div>
          ) : history && history.length > 0 ? (
            <div className="border-l-2 border-slate-600 ml-3 pl-4 space-y-3">
              {history.map((ev) => (
                <div key={ev.id} className="relative">
                  <div
                    className={`absolute -left-[22px] top-4 w-2.5 h-2.5 rounded-full ring-2 ring-slate-900 ${
                      ev.new_status === "banned" || ev.new_status === "restricted"
                        ? "bg-red-500"
                        : ev.new_status === "legal"
                          ? "bg-green-500"
                          : "bg-slate-500"
                    }`}
                  />
                  <BanEventCard
                    event={{
                      format: ev.format,
                      oldStatus: ev.old_status,
                      newStatus: ev.new_status,
                      changedAt: ev.changed_at,
                    }}
                    showCardInfo={false}
                  />
                </div>
              ))}
            </div>
          ) : (
            <p
              className="text-sm text-slate-400"
              data-testid="ban-history-empty-card"
            >
              {t("banHistory.noEventsCard")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

