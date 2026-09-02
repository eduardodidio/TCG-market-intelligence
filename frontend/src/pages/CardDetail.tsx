import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import { fetchCardDetail } from "../api/cards";
import { refreshCardPrice } from "../api/collection";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { formatDate, formatPriceOrFallback } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";
import { BatchAddModal } from "../components/BatchAddModal";
import { Breadcrumb } from "../components/Breadcrumb";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
import { ErrorBanner } from "../components/ErrorBanner";
import { PriceChart } from "../components/PriceChart";
import { SkeletonChartPanel, SkeletonInfoPanel } from "../components/Skeleton";
import type { CardDetail as CardDetailType } from "../types/api";

function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    myp: "MYP Cards",
  };
  return labels[source] ?? source;
}

export function CardDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const cardId = Number(id);

  const { isAuthenticated } = useAuth();
  const { currency } = useCurrency();
  const { getCardName, getSubtitleName } = useCardName();
  const [showBatchAdd, setShowBatchAdd] = useState(false);

  const detailFetcher = useCallback(
    () => fetchCardDetail(cardId, { currency }),
    [cardId, currency],
  );

  const { data: card, loading, error, refetch, setData: setCard } = useApi<CardDetailType>(
    detailFetcher,
    [cardId, currency],
  );

  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleRefresh = useCallback(async () => {
    if (refreshing || !card?.collection_entry_id) return;
    setRefreshing(true);
    setRefreshMsg(null);
    try {
      const params: Record<string, string> = {};
      if (currency !== "BRL") params.currency = currency;
      const res = await refreshCardPrice(
        card.collection_entry_id,
        Object.keys(params).length > 0 ? params : undefined,
      );
      if (res.data) {
        // Update the displayed price from the refreshed collection entry
        setCard({
          ...card,
          latest_price: res.data.latest_price,
        });
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
  }, [refreshing, card, currency, t, setCard]);

  // Set page title
  useEffect(() => {
    if (card) {
      document.title = `${getCardName(card.name_en, card.name_pt, t("common.unknownCard"))} | TCG Market`;
    } else {
      document.title = t("cardDetail.pageTitle");
    }
  }, [card]);

  if (loading) {
    return (
      <div data-testid="page-card-detail">
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
    // Check if it's a 404-style error
    const is404 =
      error.toLowerCase().includes("not found") ||
      error.includes("HTTP_404") ||
      error.includes("404");

    if (is404) {
      return (
        <div data-testid="page-card-detail">
          <div data-testid="card-not-found" className="text-center py-12">
            <h2 className="text-2xl font-bold text-white mb-4">{t("cardDetail.notFoundTitle")}</h2>
            <p className="text-slate-400 mb-6">
              {t("cardDetail.notFoundMessage")}
            </p>
            <Link
              to="/cards"
              className="inline-block rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {t("cardDetail.backToCards")}
            </Link>
          </div>
        </div>
      );
    }

    return (
      <div data-testid="page-card-detail">
        <ErrorBanner message={error} variant="full" onRetry={refetch} />
      </div>
    );
  }

  if (!card) {
    return (
      <div data-testid="page-card-detail">
        <div data-testid="card-not-found" className="text-center py-12">
          <h2 className="text-2xl font-bold text-white mb-4">{t("cardDetail.notFoundTitle")}</h2>
          <Link
            to="/cards"
            className="inline-block rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {t("cardDetail.backToCards")}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="page-card-detail">
      <Breadcrumb
        items={[
          { label: t("cardDetail.breadcrumbCards"), to: "/cards" },
          { label: getCardName(card.name_en, card.name_pt, t("common.unknownCard")) },
        ]}
      />

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left panel: Card info */}
        <div data-testid="card-info-panel" className="bg-slate-800 border border-slate-600 rounded-lg p-6">
          {/* Card image with dual fallback */}
          <CardImage
            setCode={card.set_code}
            collectorNumber={card.collector_number}
            nameEn={card.name_en}
            alt={getCardName(card.name_en, card.name_pt, t("common.unknownCard"))}
          />

          {/* Card name */}
          <h1 className="text-2xl font-bold text-white mb-1">{getCardName(card.name_en, card.name_pt, t("common.unknownCard"))}</h1>
          {(() => {
            const subtitle = getSubtitleName(card.name_en, card.name_pt, t("common.unknownCard"));
            return subtitle ? (
              <p className="text-sm text-slate-400 mb-4" data-testid="card-name-subtitle">{subtitle}</p>
            ) : null;
          })()}

          {/* Set and collector number */}
          <div className="flex items-center gap-3 mb-4">
            {card.set_code && (
              <span className="rounded bg-slate-700 px-2 py-1 text-xs font-mono text-slate-400">
                {card.set_code}
              </span>
            )}
            {card.collector_number && (
              <span className="text-sm text-slate-400">
                #{card.collector_number}
              </span>
            )}
          </div>

          {/* Game badge */}
          <span className="inline-block rounded-full bg-indigo-500/20 px-3 py-1 text-xs font-medium text-indigo-400 mb-6">
            {card.game}
          </span>

          {/* Latest price */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-sm text-slate-400">{t("cardDetail.latestPrice")}</p>
              {card.collection_entry_id != null && (
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
            {(() => {
              const formattedPrice = formatPriceOrFallback(card.latest_price, currency);
              return formattedPrice ? (
                <p data-testid="latest-price" className="text-3xl font-bold text-white flex items-center gap-2">
                  <CurrencyIndicator currency={currency} size={24} />
                  {formattedPrice}
                </p>
              ) : (
                <p data-testid="latest-price" className="text-3xl font-bold text-slate-500">
                  {t("common.noPriceData")}
                </p>
              );
            })()}
            {refreshMsg && (
              <p
                data-testid="refresh-message"
                className={`text-xs mt-1 ${refreshMsg.type === "success" ? "text-green-400" : "text-red-400"}`}
              >
                {refreshMsg.text}
              </p>
            )}
          </div>

          {/* Source links */}
          {card.source_cards.length > 0 && (
            <div className="mb-6">
              <p className="text-sm text-slate-400 mb-2">{t("cardDetail.sources")}</p>
              <div className="flex flex-wrap gap-2">
                {card.source_cards.map((sc) => (
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

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-400">{t("cardDetail.firstTracked")}</p>
              <p className="text-white">{formatDate(card.created_at)}</p>
            </div>
            <div>
              <p className="text-slate-400">{t("cardDetail.lastUpdated")}</p>
              <p className="text-white">{formatDate(card.updated_at)}</p>
            </div>
          </div>

          {/* External Links */}
          <div className="mt-6" data-testid="external-links">
            <p className="text-sm text-slate-400 mb-2">{t("cardDetail.externalLinks")}</p>
            <div className="flex flex-wrap gap-2">
              <a
                href={`https://scryfall.com/search?q=${encodeURIComponent(card.name_en)}${card.set_code ? `+set:${card.set_code}` : ""}`}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="scryfall-link"
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                {t("cardDetail.viewOnScryfall")}
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
              <a
                href={`https://www.ligamagic.com.br/?view=cards/card&card=${encodeURIComponent(card.name_en)}`}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="ligamagic-link"
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                {t("cardDetail.viewOnLigaMagic")}
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
            </div>
          </div>

          {/* Add to Collection CTA */}
          {card.collection_entry_id == null && (
            <div className="mt-6" data-testid="add-to-collection-section">
              {isAuthenticated ? (
                <button
                  data-testid="add-to-collection-btn"
                  onClick={() => setShowBatchAdd(true)}
                  className="inline-flex items-center gap-2 rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                >
                  + {t("cardDetail.addToCollection")}
                </button>
              ) : (
                <Link
                  to="/login"
                  className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                  data-testid="sign-in-to-add-link"
                >
                  {t("cardDetail.signInToAdd")}
                </Link>
              )}
            </div>
          )}
        </div>

        {/* Right panel: Price chart */}
        <div>
          <PriceChart cardId={cardId} currency={currency} />
        </div>
      </div>

      {/* Batch Add Modal (pre-filled with card name) */}
      {showBatchAdd && card && (
        <BatchAddModal
          isOpen={showBatchAdd}
          onClose={() => setShowBatchAdd(false)}
          onSuccess={() => {
            setShowBatchAdd(false);
            refetch();
          }}
          initialText={`1 ${card.name_en}${card.set_code ? ` [${card.set_code}]` : ""}`}
        />
      )}
    </div>
  );
}

/** Card image with dual fallback: set/number -> name -> placeholder */
function CardImage({
  setCode,
  collectorNumber,
  nameEn,
  alt,
}: {
  setCode: string | null;
  collectorNumber: string | null;
  nameEn: string;
  alt: string;
}) {
  const [imgError, setImgError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);

  const primaryUrl =
    setCode && collectorNumber
      ? scryfallImageUrl(setCode, collectorNumber, "normal")
      : null;
  const fallbackUrl = nameEn ? scryfallImageByName(nameEn, "normal") : null;

  // If no primary URL, go straight to fallback
  let currentUrl: string | null;
  let showImage: boolean;

  if (primaryUrl) {
    // Has primary: primary -> fallback -> placeholder
    currentUrl = imgError && fallbackUrl ? fallbackUrl : primaryUrl;
    showImage = !!currentUrl && !(imgError && (fallbackError || !fallbackUrl));
  } else {
    // No primary: fallback -> placeholder
    currentUrl = fallbackUrl;
    showImage = !!fallbackUrl && !fallbackError;
  }

  return (
    <div className="mb-6 flex justify-center">
      {showImage && currentUrl ? (
        <img
          src={currentUrl}
          alt={alt}
          data-testid="card-image"
          className="rounded-lg shadow-lg max-w-[250px] w-full"
          loading="eager"
          onError={() => {
            if (primaryUrl && !imgError) {
              setImgError(true);
            } else {
              setFallbackError(true);
            }
          }}
        />
      ) : (
        <div
          data-testid="card-image-placeholder"
          className="flex items-center justify-center bg-gradient-to-br from-slate-700 to-slate-800 rounded-lg max-w-[250px] w-full aspect-[5/7]"
        >
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
        </div>
      )}
    </div>
  );
}
