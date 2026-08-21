import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { CardSummary } from "../types/api";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { formatPriceOrFallback } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

interface CardTileProps {
  card: CardSummary;
}

export function CardTile({ card }: CardTileProps) {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const { getCardName } = useCardName();
  const displayName = getCardName(card.name_en, card.name_pt, t("common.unknownCard"));
  const [imgError, setImgError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);

  // Primary: set/collector_number URL. Fallback: name-based URL.
  const primaryUrl =
    card.set_code && card.collector_number
      ? scryfallImageUrl(card.set_code, card.collector_number)
      : null;
  const fallbackUrl = card.name_en ? scryfallImageByName(card.name_en) : null;

  const currentUrl = imgError && fallbackUrl ? fallbackUrl : primaryUrl;
  const showImage = currentUrl && !(imgError && (fallbackError || !fallbackUrl));

  return (
    <Link
      to={`/cards/${card.id}`}
      className="group block bg-slate-800 rounded-lg overflow-hidden
        border border-slate-600 hover:border-cyan-400/50
        transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
      data-testid={`card-tile-${card.id}`}
    >
      {/* Card image */}
      <div
        className="aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800
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
          {card.collector_number && (
            <span className="text-xs text-slate-500">
              #{card.collector_number}
            </span>
          )}
        </div>

        {(() => {
          const formattedPrice = formatPriceOrFallback(card.latest_price, currency);
          return formattedPrice ? (
            <p className="mt-2 text-sm font-bold text-cyan-400" data-testid="card-price">
              {formattedPrice}
            </p>
          ) : (
            <p className="mt-2 text-sm text-slate-500" data-testid="card-price">
              {t("common.noPriceData")}
            </p>
          );
        })()}
      </div>
    </Link>
  );
}
