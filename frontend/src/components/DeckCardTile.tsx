import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { DeckCard } from "../types/api";
import { useCardName } from "../hooks/useCardName";
import { useCredits } from "../hooks/useCredits";
import { formatBRL } from "../utils/format";
import { CreditConfirmModal } from "./CreditConfirmModal";

interface DeckCardTileProps {
  card: DeckCard;
  onRefresh?: (entryId: number) => Promise<void>;
}

export function DeckCardTile({ card, onRefresh }: DeckCardTileProps) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();
  const [refreshing, setRefreshing] = useState(false);
  const [creditModalOpen, setCreditModalOpen] = useState(false);
  const { balance, isAdmin, refetch: refetchCredits } = useCredits();
  const displayName = getCardName(card.name_en, card.name_pt, t("common.unknownCard"));
  const linkTo = card.in_collection && card.collection_entry_id
    ? `/collection/${card.collection_entry_id}`
    : card.card_id
      ? `/cards/${card.card_id}`
      : undefined;

  const content = (
    <div
      className={`group relative rounded-lg overflow-hidden bg-slate-800 border transition-all duration-200 ${
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
            alt={displayName}
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

        {/* Refresh button */}
        {card.in_collection && card.collection_entry_id != null && card.card_id != null && onRefresh && (
          <button
            data-testid={`refresh-deck-card-${card.id}`}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setCreditModalOpen(true);
            }}
            disabled={refreshing}
            title={refreshing ? t("collection.refreshing") : t("collection.refresh")}
            className="absolute bottom-2 right-2 w-6 h-6 flex items-center justify-center rounded-full bg-black/60 text-slate-300 hover:text-cyan-400 hover:bg-black/80 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-100 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <svg
              className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`}
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

      {/* Card info */}
      <div className="p-2">
        <p
          className="text-sm font-medium text-white truncate"
          data-testid="card-name"
        >
          {displayName}
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

  const modal = (
    <CreditConfirmModal
      isOpen={creditModalOpen}
      onCancel={() => setCreditModalOpen(false)}
      onConfirm={async () => {
        setCreditModalOpen(false);
        if (!onRefresh || card.collection_entry_id == null) return;
        setRefreshing(true);
        try {
          await onRefresh(card.collection_entry_id);
        } catch (err: unknown) {
          const status = (err as { status?: number })?.status;
          if (status === 402) refetchCredits();
        } finally {
          setRefreshing(false);
        }
      }}
      cost={1}
      balance={balance ?? 0}
      actionLabel={t("credits.refreshCost")}
      isAdmin={isAdmin}
    />
  );

  if (linkTo) {
    return (
      <>
        <Link to={linkTo} data-testid={`deck-card-link-${card.id}`}>
          {content}
        </Link>
        {modal}
      </>
    );
  }

  return <>{content}{modal}</>;
}
