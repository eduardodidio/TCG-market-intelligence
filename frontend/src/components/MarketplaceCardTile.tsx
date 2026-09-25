import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { MarketplaceListing } from "../api/marketplace";
import { CopyCodeButton } from "./CopyCodeButton";
import { Card3DTilt } from "./Card3DTilt";
import { CardPreviewModal } from "./CardPreviewModal";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency } from "../utils/format";
import { isPromoCard } from "../utils/promo";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

export interface MarketplaceCardTileProps {
  listing: MarketplaceListing;
  onInterest: (listing: MarketplaceListing) => void;
  compact?: boolean;
}

export function MarketplaceCardTile({ listing, onInterest, compact = false }: MarketplaceCardTileProps) {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const { getCardName } = useCardName();
  const [imgError, setImgError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  const displayName = getCardName(listing.card_name_en, listing.card_name_pt, t("common.unknownCard"));
  const primaryUrl = scryfallImageUrl(listing.set_code, listing.collector_number);
  const fallbackUrl = listing.card_name_en ? scryfallImageByName(listing.card_name_en) : null;
  const currentUrl = imgError && fallbackUrl ? fallbackUrl : primaryUrl;
  const showImage = !(imgError && (fallbackError || !fallbackUrl));

  return (
    <Card3DTilt foil={false} className="w-full">
    <div
      className="group block bg-slate-800 rounded-lg overflow-hidden border border-slate-600
        hover:border-cyan-400/50 transition-all duration-300 hover:shadow-lg relative"
      data-testid={`marketplace-card-${listing.entry_id}`}
    >
      {listing.quantity > 1 && (
        <span className="absolute top-2 right-2 z-10 bg-indigo-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
          x{listing.quantity}
        </span>
      )}

      <div
        className={`aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center overflow-hidden${showImage ? " cursor-zoom-in" : ""}`}
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
              if (!imgError) setImgError(true);
              else setFallbackError(true);
            }}
          />
        ) : (
          <span className="text-slate-500 text-xs text-center px-2">{displayName}</span>
        )}
      </div>

      <div className={compact ? "p-2 space-y-1" : "p-3 space-y-1.5"}>
        <h3 className="text-sm font-semibold text-white truncate" title={displayName}>
          {displayName}
        </h3>
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{listing.set_code.toUpperCase()} #{listing.collector_number}</span>
          {listing.rarity && (
            <span className={
              listing.rarity === "M" ? "text-amber-400" :
              listing.rarity === "R" ? "text-yellow-500" :
              listing.rarity === "U" ? "text-slate-400" : "text-slate-500"
            }>
              {listing.rarity}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-cyan-400">
            {listing.latest_price != null
              ? formatCurrency(listing.latest_price, currency)
              : t("common.noData")}
          </span>
          {!compact && (
            <span className="text-xs text-amber-400" title={t("marketplace.estimatedFee", { fee: listing.estimated_fee })}>
              {listing.estimated_fee} {t("marketplace.tokens")}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => onInterest(listing)}
          className="w-full mt-1.5 px-3 py-1.5 text-xs font-medium bg-cyan-600 hover:bg-cyan-500
            text-white rounded-md transition-colors duration-200"
          data-testid={`interest-btn-${listing.entry_id}`}
        >
          {t("marketplace.interested")}
        </button>

        {!compact && (
          <div className="text-center mt-1">
            <CopyCodeButton code={listing.share_code} />
          </div>
        )}
      </div>
    </div>
    {previewOpen && currentUrl && (
      <CardPreviewModal
        imageUrl={currentUrl}
        cardName={displayName}
        isFoil={false}
        isPromo={isPromoCard(listing.set_code, null)}
        onClose={() => setPreviewOpen(false)}
      />
    )}
    </Card3DTilt>
  );
}
