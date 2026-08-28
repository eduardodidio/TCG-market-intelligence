import { useTranslation } from "react-i18next";
import { useValuation } from "../hooks/useValuation";
import { formatCurrency } from "../utils/format";

interface ValuationBadgeProps {
  days?: number;
  currency?: string;
}

export function ValuationBadge({ days = 7, currency = "BRL" }: ValuationBadgeProps) {
  const { t } = useTranslation();
  const { data, loading } = useValuation(days, currency);

  if (loading) {
    return (
      <span
        className="inline-flex items-center gap-1 text-sm text-slate-500"
        data-testid="valuation-loading"
      >
        --
      </span>
    );
  }

  if (!data || data.change_pct == null) {
    return (
      <span
        className="inline-flex items-center gap-1 text-sm text-slate-500"
        data-testid="valuation-no-history"
        title={t("valuation.noHistory")}
      >
        --
      </span>
    );
  }

  const isPositive = data.change_pct >= 0;
  const colorClass = isPositive ? "text-emerald-400" : "text-red-400";
  const arrow = isPositive ? "\u2191" : "\u2193";
  const sign = isPositive ? "+" : "";
  const absChange = data.change_abs != null ? formatCurrency(Math.abs(data.change_abs), currency) : "";
  const direction = isPositive ? t("valuation.up") : t("valuation.down");
  const tooltipText = `${direction} ${absChange}`;

  return (
    <span
      className={`inline-flex items-center gap-1 text-sm font-semibold ${colorClass}`}
      data-testid="valuation-badge"
      title={tooltipText}
    >
      <span aria-hidden="true">{arrow}</span>
      <span>{sign}{data.change_pct.toFixed(2)}%</span>
    </span>
  );
}
