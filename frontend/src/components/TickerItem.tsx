import { useTranslation } from "react-i18next";
import { useCardName } from "../hooks/useCardName";
import { formatCurrency } from "../utils/format";
import type { TickerItemData } from "../types/api";

interface TickerItemProps {
  item: TickerItemData;
  onClick: (cardId: number) => void;
  tabIndex?: number;
}

export function TickerItem({ item, onClick, tabIndex }: TickerItemProps) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();

  const name = getCardName(item.name_en, item.name_pt);
  const price = formatCurrency(item.price_end, item.currency);
  const changePct = Math.abs(item.change_pct).toFixed(1);
  const isUp = item.direction === "up";
  const arrow = isUp ? "\u25B2" : "\u25BC";
  const colorClass = isUp ? "text-emerald-400" : "text-red-400";
  const sign = isUp ? "+" : "-";
  const directionLabel = t(`ticker.${item.direction}`);

  return (
    <button
      className="inline-flex items-center gap-2 px-4 py-1.5 border-r border-slate-600 cursor-pointer hover:bg-slate-700/50 transition-colors whitespace-nowrap"
      onClick={() => onClick(item.card_id)}
      tabIndex={tabIndex}
      aria-label={t("ticker.itemAriaLabel", {
        name,
        price,
        direction: directionLabel,
        change: changePct,
      })}
      data-testid="ticker-item"
    >
      {item.set_code && (
        <span className="text-slate-500 text-xs font-mono uppercase">
          {item.set_code}
        </span>
      )}
      <span className="text-slate-200 text-sm truncate max-w-[120px]">
        {name}
      </span>
      <span className="text-slate-200 text-sm">{price}</span>
      <span className={`text-sm ${colorClass}`}>
        {arrow} {sign}{changePct}%
      </span>
    </button>
  );
}
