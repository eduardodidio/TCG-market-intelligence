import { useTranslation } from "react-i18next";
import { formatCurrency } from "../utils/format";

interface PnlBadgeProps {
  acquisitionPrice: number;
  currentPrice: number;
  currency?: string;
}

/**
 * Shows unrealized P&L for a card.
 * Format: "+R$ 15,30 (+23.4%)" in green, or "-R$ 5,00 (-12.1%)" in red.
 * Only renders when both acquisition and current prices are available.
 */
export function PnlBadge({ acquisitionPrice, currentPrice, currency = "BRL" }: PnlBadgeProps) {
  const { t } = useTranslation();

  const pnl = currentPrice - acquisitionPrice;
  const pnlPct = acquisitionPrice > 0 ? (pnl / acquisitionPrice) * 100 : 0;
  const isPositive = pnl >= 0;

  const colorClass = isPositive ? "text-emerald-400" : "text-red-400";
  const sign = isPositive ? "+" : "";

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold ${colorClass}`}
      data-testid="pnl-badge"
      title={t("portfolio.pnlTooltip")}
    >
      <span>
        {sign}{formatCurrency(pnl, currency)}
      </span>
      <span className="opacity-75">
        ({sign}{pnlPct.toFixed(1)}%)
      </span>
    </span>
  );
}
