import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { CardSummary } from "../types/api";
import type { PriceTrendEntry } from "../api/cards";
import { refreshCardPrice } from "../api/cards";
import { useAuth } from "../hooks/useAuth";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { usePriceRequestPolling } from "../hooks/usePriceRequestPolling";
import { formatPriceOrFallback } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";
import { Card3DTilt } from "./Card3DTilt";
import { CardPreviewModal } from "./CardPreviewModal";
import { PriceSparkline } from "./PriceSparkline";
import { TrendBadge } from "./TrendBadge";

export interface CardTileProps {
  card: CardSummary;
  trend?: PriceTrendEntry;
  onPriceRefreshed?: (cardId: number, newPrice: number | null) => void;
  /** Override the default navigation target (`/cards/{id}`). */
  linkTo?: string;
  /** When true, enables foil shimmer effect on the 3D tilt and preview modal. */
  isFoil?: boolean;
}

export function CardTile({ card, trend, onPriceRefreshed, linkTo, isFoil }: CardTileProps) {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const { getCardName } = useCardName();
  const { isAuthenticated } = useAuth();
  const displayName = getCardName(card.name_en, card.name_pt, t("common.unknownCard"));
  const [imgError, setImgError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [queued, setQueued] = useState(false);
  const [refreshError, setRefreshError] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [failed, setFailed] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  // Poll for price request status after queuing
  const { status: requestStatus, isPolling } = usePriceRequestPolling({
    cardId: card.id,
    enabled: queued,
    onCompleted: (price) => {
      setQueued(false);
      setCompleted(true);
      setTimeout(() => setCompleted(false), 1500);
      if (price !== null && onPriceRefreshed) {
        onPriceRefreshed(card.id, price);
      }
    },
    onFailed: () => {
      setQueued(false);
      setFailed(true);
      setTimeout(() => setFailed(false), 3000);
    },
  });

  // Primary: set/collector_number URL. Fallback: name-based URL.
  const primaryUrl =
    card.set_code && card.collector_number
      ? scryfallImageUrl(card.set_code, card.collector_number)
      : null;
  const fallbackUrl = card.name_en ? scryfallImageByName(card.name_en) : null;

  const currentUrl = imgError && fallbackUrl ? fallbackUrl : primaryUrl;
  const showImage = currentUrl && !(imgError && (fallbackError || !fallbackUrl));

  const currentPrice = card.latest_price;

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

  // Button color
  const buttonColor = refreshError || failed
    ? "text-red-400"
    : completed
      ? "text-green-400"
      : queued
        ? pollingTimedOut
          ? "text-yellow-400"
          : "text-cyan-400"
        : "text-slate-300 hover:text-cyan-400";

  // Button title
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
    <Card3DTilt foil={isFoil ?? false} className="w-full">
    <Link
      to={linkTo ?? `/cards/${card.id}`}
      className="group block bg-white dark:bg-slate-800 rounded-lg overflow-hidden
        border border-gray-200 dark:border-slate-600 hover:border-cyan-400/50
        transition-all duration-200 hover:shadow-lg relative"
      data-testid={`card-tile-${card.id}`}
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
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
              data-testid="error-icon"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          ) : completed ? (
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
              data-testid="check-icon"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          ) : queued && isPolling ? (
            <svg
              className="h-3.5 w-3.5 animate-spin"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
              data-testid="spinner-icon"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          ) : pollingTimedOut ? (
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
              data-testid="clock-icon"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          ) : (
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
          )}
        </button>
      )}

      {/* Card image */}
      <div
        className={`aspect-[5/7] bg-gradient-to-br from-gray-200 dark:from-slate-700 to-gray-300 dark:to-slate-800
          flex items-center justify-center overflow-hidden${showImage ? " cursor-zoom-in" : ""}`}
        data-testid="card-image-placeholder"
        {...(showImage
          ? {
              onClick: (e: React.MouseEvent) => {
                e.preventDefault();
                e.stopPropagation();
                setPreviewOpen(true);
              },
            }
          : {})}
      >
        {showImage ? (
          <img
            src={currentUrl}
            alt={displayName}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => {
              if (!imgError) {
                setImgError(true);
              } else {
                setFallbackError(true);
              }
            }}
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
          className="text-sm font-semibold text-gray-900 dark:text-white truncate group-hover:text-cyan-400 transition-colors"
          title={displayName}
        >
          {displayName}
        </h3>

        <div className="flex items-center gap-2 mt-1">
          {card.set_code && (
            <span className="inline-block px-1.5 py-0.5 text-xs font-mono bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 rounded">
              {card.set_code}
            </span>
          )}
          {card.collector_number && (
            <span className="text-xs text-gray-400 dark:text-slate-500">
              #{card.collector_number}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 mt-2">
          {(() => {
            const formattedPrice = formatPriceOrFallback(currentPrice, currency);
            return formattedPrice ? (
              <span className="text-sm font-bold text-cyan-400" data-testid="card-price">
                {formattedPrice}
              </span>
            ) : (
              <span className="text-sm text-gray-400 dark:text-slate-500" data-testid="card-price">
                {t("common.noPriceData")}
              </span>
            );
          })()}
          {trend && trend.change_pct !== null && (
            <TrendBadge changePct={trend.change_pct} />
          )}
        </div>
        {(queued && isPolling) && (
          <span className="text-xs text-cyan-500 dark:text-cyan-400 mt-1 block" data-testid="queued-feedback">
            {t("cards.priceUpdateProcessing")}
          </span>
        )}
        {pollingTimedOut && (
          <span className="text-xs text-yellow-500 dark:text-yellow-400 mt-1 block" data-testid="queued-feedback">
            {t("cards.priceUpdateTimeout")}
          </span>
        )}
        {completed && (
          <span className="text-xs text-green-500 dark:text-green-400 mt-1 block" data-testid="completed-feedback">
            {t("cards.priceUpdateCompleted")}
          </span>
        )}
        {failed && (
          <span className="text-xs text-red-500 dark:text-red-400 mt-1 block" data-testid="failed-feedback">
            {t("cards.priceUpdateFailed")}
          </span>
        )}
        {refreshError && (
          <span className="text-xs text-red-500 dark:text-red-400 mt-1 block" data-testid="refresh-error-feedback">
            {t("cards.priceRefreshError")}
          </span>
        )}
        {trend && trend.prices.length > 1 && (
          <div className="mt-1" data-testid="card-sparkline">
            <PriceSparkline prices={trend.prices} height={24} />
          </div>
        )}
      </div>
    </Link>
    {previewOpen && currentUrl && (
      <CardPreviewModal
        imageUrl={currentUrl}
        cardName={displayName}
        isFoil={isFoil}
        onClose={() => setPreviewOpen(false)}
      />
    )}
    </Card3DTilt>
  );
}
