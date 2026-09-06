import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { CardSummary } from "../types/api";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { formatPriceOrFallback } from "../utils/format";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";
import { CardImage } from "./CardImage";
import { PriceSparkline } from "./PriceSparkline";
import { TrendBadge } from "./TrendBadge";
import type { PriceTrendEntry } from "../api/cards";

interface CardTileProps {
  card: CardSummary;
  trend?: PriceTrendEntry;
}

export function CardTile({ card, trend }: CardTileProps) {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const { getCardName } = useCardName();
  const displayName = getCardName(card.name_en, card.name_pt, t("common.unknownCard"));

  const primaryUrl =
    card.set_code && card.collector_number
      ? scryfallImageUrl(card.set_code, card.collector_number)
      : null;
  const fallbackUrl = card.name_en ? scryfallImageByName(card.name_en) : null;

  return (
    <Link
      to={`/cards/${card.id}`}
      className="group block bg-slate-800 rounded-lg overflow-hidden
        border border-slate-600 hover:border-cyan-400/50
        transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
      data-testid={`card-tile-${card.id}`}
    >
      {/* Card image with skeleton loading */}
      <div
        className="aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800
          flex items-center justify-center overflow-hidden"
        data-testid="card-image-placeholder"
      >
        <CardImage
          src={primaryUrl}
          fallbackSrc={fallbackUrl}
          alt={displayName}
        />
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
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <p className="text-sm font-bold text-cyan-400" data-testid="card-price">
                  {formattedPrice}
                </p>
                {trend && <TrendBadge changePct={trend.change_pct} size="sm" />}
              </div>
              {trend && trend.prices.length >= 2 && (
                <div className="mt-1">
                  <PriceSparkline prices={trend.prices} />
                </div>
              )}
            </div>
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
