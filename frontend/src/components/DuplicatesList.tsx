import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { DuplicateCard } from "../types/tradeMatch";
import { Card3DTilt } from "./Card3DTilt";
import { CardImage } from "./CardImage";
import { CardPreviewModal } from "./CardPreviewModal";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

interface DuplicatesListProps {
  duplicates: DuplicateCard[];
  compact?: boolean;
}

function getImageSrc(card: DuplicateCard): string | null {
  if (card.image_uri) return card.image_uri;
  if (card.set_code && card.collector_number) {
    return scryfallImageUrl(card.set_code, card.collector_number, "normal");
  }
  if (card.name_en) {
    return scryfallImageByName(card.name_en, "normal");
  }
  return null;
}

function DuplicateCardTile({ card }: { card: DuplicateCard }) {
  const { t } = useTranslation();
  const [previewOpen, setPreviewOpen] = useState(false);
  const imgSrc = getImageSrc(card);

  return (
    <Card3DTilt foil={false} className="w-full">
      <Link
        to={`/cards/${card.card_id}`}
        className="relative flex flex-col bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden hover:border-indigo-500 dark:hover:border-indigo-400 transition-colors no-underline"
        data-testid="duplicate-card"
      >
        {/* Surplus badge */}
        <div className="absolute top-2 right-2 z-10">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-green-500 text-white">
            x{card.quantity}
          </span>
        </div>

        {/* Card image */}
        <div
          className={`aspect-[5/7] bg-gray-100 dark:bg-slate-700${imgSrc ? " cursor-zoom-in" : ""}`}
          {...(imgSrc
            ? {
                onClick: (e: React.MouseEvent) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setPreviewOpen(true);
                },
              }
            : {})}
        >
          <CardImage
            src={imgSrc}
            alt={card.name_en ?? "Card"}
            className="w-full h-full object-cover"
          />
        </div>

        {/* Card info */}
        <div className="p-2 flex-1">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {card.name_en ?? t("common.unknownCard")}
          </p>
          {card.set_code && (
            <p className="text-xs text-gray-500 dark:text-slate-400 uppercase">
              {card.set_code}
              {card.collector_number ? ` #${card.collector_number}` : ""}
            </p>
          )}
          <p className="text-xs text-green-600 dark:text-green-400 mt-1">
            {t("tradeMatch.surplus")}: {card.surplus}
          </p>
        </div>
      </Link>
      {previewOpen && imgSrc && (
        <CardPreviewModal
          imageUrl={imgSrc}
          cardName={card.name_en ?? "Card"}
          isFoil={false}
          onClose={() => setPreviewOpen(false)}
        />
      )}
    </Card3DTilt>
  );
}

export function DuplicatesList({
  duplicates,
  compact = false,
}: DuplicatesListProps) {
  if (duplicates.length === 0) {
    return null;
  }

  return (
    <div
      className={`grid gap-3 ${
        compact
          ? "grid-cols-2 sm:grid-cols-3 md:grid-cols-4"
          : "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
      }`}
      data-testid="duplicates-list"
    >
      {duplicates.map((card) => (
        <DuplicateCardTile key={card.card_id} card={card} />
      ))}
    </div>
  );
}
