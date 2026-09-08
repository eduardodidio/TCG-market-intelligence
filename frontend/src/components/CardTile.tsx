import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { CardSummary } from "../types/api";
import type { PriceTrendEntry } from "../api/cards";
import { refreshCardPrice } from "../api/cards";
import { useAuth } from "../hooks/useAuth";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { formatPriceOrFallback } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";
import { PriceSparkline } from "./PriceSparkline";
import { TrendBadge } from "./TrendBadge";

export interface CardTileProps {
  card: CardSummary;
  trend?: PriceTrendEntry;
  onPriceRefreshed?: (cardId: number, newPrice: number | null) => void;
}

export function CardTile({ card, trend, onPriceRefreshed }: CardTileProps) {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const { getCardName } = useCardName();
  const { isAuthenticated } = useAuth();
  const displayName = getCardName(card.name_en, card.name_pt, t("common.unknownCard"));
  const [imgError, setImgError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [displayPrice, setDisplayPrice] = useState<number | null | undefined>(undefined);

  // Primary: set/collector_number URL. Fallback: name-based URL.
  const primaryUrl =
    card.set_code && card.collector_number
      ? scryfallImageUrl(card.set_code, card.collector_number)
      : null;
  const fallbackUrl = card.name_en ? scryfallImageByName(card.name_en) : null;

  const currentUrl = imgError && fallbackUrl ? fallbackUrl : primaryUrl;
  const showImage = currentUrl && !(imgError && (fallbackError || !fallbackUrl));

  const currentPrice = displayPrice !== undefined ? displayPrice : card.latest_price;

  const handleRefresh = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (refreshing) return;

    setRefreshing(true);
    try {
      const res = await refreshCardPrice(card.id);
      if (res.data) {
        setDisplayPrice(res.data.latest_price);
        onPriceRefreshed?.(card.id, res.data.latest_price);
      }
    } catch {
      // silently fail
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <Link
      to={`/cards/${card.id}`}
      className="group block bg-white dark:bg-slate-800 rounded-lg overflow-hidden
        border border-gray-200 dark:border-slate-600 hover:border-cyan-400/50
        transition-all duration-200 hover:scale-[1.02] hover:shadow-lg relative"
      data-testid={`card-tile-${card.id}`}
    >
      {/* Refresh button overlay */}
      {isAuthenticated && (
        <button
          data-testid={`refresh-card-price-${card.id}`}
          onClick={handleRefresh}
          disabled={refreshing}
          title={t("credits.refreshCostTooltip", { cost: 1 })}
          className="absolute top-2 right-2 z-10 w-7 h-7 flex items-center justify-center rounded-full
            bg-black/60 text-slate-300 hover:text-cyan-400 hover:bg-black/80
            opacity-0 group-hover:opacity-100 transition-all
            disabled:opacity-100 disabled:cursor-not-allowed
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
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
        </button>
      )}

      {/* Card image */}
      <div
        className="aspect-[5/7] bg-gradient-to-br from-gray-200 dark:from-slate-700 to-gray-300 dark:to-slate-800
          flex items-center justify-center overflow-hidden"
        data-testid="card-image-placeholder"
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
        {trend && trend.prices.length > 1 && (
          <div className="mt-1" data-testid="card-sparkline">
            <PriceSparkline prices={trend.prices} height={24} />
          </div>
        )}
      </div>
    </Link>
  );
}
