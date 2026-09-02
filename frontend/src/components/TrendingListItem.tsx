import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useCardName } from "../hooks/useCardName";
import type { TrendingCardEntry } from "../types/api";

interface TrendingListItemProps {
  entry: TrendingCardEntry;
  ownedCardIds?: Set<number>;
}

function formatCurrency(value: number, currency: string): string {
  if (currency === "USD") return `$${value.toFixed(2)}`;
  if (currency === "PILA") return `${value.toFixed(2)} pilas`;
  return `R$${value.toFixed(2)}`;
}

export function TrendingListItem({ entry, ownedCardIds }: TrendingListItemProps) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();

  const isUp = entry.change_pct > 0;
  const sign = isUp ? "+" : "";
  const changeColor = isUp ? "text-green-400" : "text-red-400";
  const displayName = getCardName(entry.name_en, entry.name_pt);
  const isOwned = ownedCardIds?.has(entry.card_id) ?? false;

  return (
    <Link
      to={`/cards/${entry.card_id}`}
      className="flex items-center justify-between gap-3 px-3 py-2 rounded-md hover:bg-slate-700/50 transition-colors"
      data-testid="trending-list-item"
    >
      {/* Left: name + set code */}
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm text-white truncate" title={displayName}>
          {displayName}
        </span>
        {entry.set_code && (
          <span className="flex-shrink-0 text-xs text-slate-400 uppercase bg-slate-700 px-1.5 py-0.5 rounded">
            {entry.set_code}
          </span>
        )}
        {isOwned && (
          <span
            className="flex-shrink-0 w-4 h-4 rounded-full bg-green-500 flex items-center justify-center"
            title={t("trending.inCollection")}
            data-testid="owned-badge"
          >
            <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </span>
        )}
      </div>

      {/* Right: % change + price */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <span className={`text-sm font-semibold ${changeColor}`}>
          {sign}{entry.change_pct.toFixed(1)}%
        </span>
        <span className="text-sm text-slate-300">
          {formatCurrency(entry.price_end, entry.currency)}
        </span>
      </div>
    </Link>
  );
}
