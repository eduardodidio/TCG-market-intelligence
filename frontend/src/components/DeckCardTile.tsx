import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { DeckCard } from "../types/api";
import { formatBRL } from "../utils/format";

interface DeckCardTileProps {
  card: DeckCard;
}

export function DeckCardTile({ card }: DeckCardTileProps) {
  const { t } = useTranslation();
  const linkTo = card.in_collection && card.collection_entry_id
    ? `/collection/${card.collection_entry_id}`
    : card.card_id
      ? `/cards/${card.card_id}`
      : undefined;

  const content = (
    <div
      className={`relative rounded-lg overflow-hidden bg-slate-800 border transition-all duration-200 ${
        card.in_collection
          ? "border-slate-600 hover:border-indigo-500 hover:shadow-lg"
          : "border-slate-600/50"
      }`}
      data-testid={`deck-card-tile-${card.id}`}
    >
      {/* Card image */}
      <div className="aspect-[488/680] bg-slate-700 relative">
        {card.image_url ? (
          <img
            src={card.image_url}
            alt={card.name_en}
            className={`w-full h-full object-cover ${
              !card.in_collection ? "opacity-50" : ""
            }`}
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div
            className={`w-full h-full flex items-center justify-center text-slate-500 text-sm ${
              !card.in_collection ? "opacity-50" : ""
            }`}
          >
            {t("common.noImage")}
          </div>
        )}

        {/* Darkened overlay for cards not in collection */}
        {!card.in_collection && (
          <div
            className="absolute inset-0 bg-black/40 flex items-center justify-center"
            data-testid="not-owned-overlay"
            title={t("common.notOwned")}
          >
            <span className="text-xs text-slate-400 bg-black/60 px-2 py-1 rounded">
              {t("common.notOwned")}
            </span>
          </div>
        )}

        {/* Quantity badge */}
        {card.quantity > 1 && (
          <span
            className="absolute top-2 right-2 bg-indigo-500 text-white text-xs font-bold px-2 py-0.5 rounded"
            data-testid="quantity-badge"
          >
            x{card.quantity}
          </span>
        )}
      </div>

      {/* Card info */}
      <div className="p-2">
        <p
          className="text-sm font-medium text-white truncate"
          data-testid="card-name"
        >
          {card.name_en}
        </p>

        <div className="flex items-center justify-between mt-1">
          <div className="flex items-center gap-1">
            {card.set_code && (
              <span className="text-xs text-slate-400 uppercase" data-testid="set-badge">
                {card.set_code}
              </span>
            )}
            {card.collector_number && (
              <span className="text-xs text-slate-500" data-testid="collector-number">
                #{card.collector_number}
              </span>
            )}
          </div>

          <span
            className="text-xs text-slate-400"
            data-testid="card-price"
          >
            {card.latest_price != null ? formatBRL(card.latest_price) : "--"}
          </span>
        </div>
      </div>
    </div>
  );

  if (linkTo) {
    return (
      <Link to={linkTo} data-testid={`deck-card-link-${card.id}`}>
        {content}
      </Link>
    );
  }

  return content;
}
