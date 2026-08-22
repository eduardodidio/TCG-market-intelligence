import { useTranslation } from "react-i18next";
import { KpiCard } from "./KpiCard";
import { CurrencyIndicator } from "./CurrencyIndicator";
import { SkeletonKpi } from "./Skeleton";
import { formatCurrency } from "../utils/format";
import type { MarketSummaryResponse } from "../types/api";

interface MarketSummaryKpisProps {
  data: MarketSummaryResponse | null;
  loading: boolean;
  currency: string;
}

export function MarketSummaryKpis({ data, loading, currency }: MarketSummaryKpisProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-5" data-testid="market-summary-loading">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonKpi key={i} />
        ))}
      </div>
    );
  }

  const cardsTracked = data?.total_cards_tracked ?? 0;
  const avgPrice = data?.avg_price ?? null;
  const avgChange = data?.avg_price_change_pct ?? null;
  const direction = data?.market_direction ?? "flat";
  const gainersCount = data?.gainers_count ?? 0;
  const losersCount = data?.losers_count ?? 0;
  const total = gainersCount + losersCount;
  const gainersRatio = total > 0 ? Math.round((gainersCount / total) * 100) : 0;

  // Direction badge styling
  const directionColors: Record<string, string> = {
    up: "bg-emerald-500/20 text-emerald-400",
    down: "bg-red-500/20 text-red-400",
    flat: "bg-slate-500/20 text-slate-400",
  };
  const directionColor = directionColors[direction] ?? directionColors.flat;
  const directionLabel = t(`marketPage.direction.${direction}`);

  // Avg change formatting
  const changeFormatted = avgChange != null
    ? `${avgChange > 0 ? "+" : ""}${avgChange.toFixed(2)}%`
    : "--";
  const changeColor = avgChange != null && avgChange > 0
    ? "text-emerald-400"
    : avgChange != null && avgChange < 0
      ? "text-red-400"
      : "text-slate-400";

  return (
    <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-5" data-testid="market-summary-kpis">
      <KpiCard
        title={t("marketPage.summary.cardsTracked")}
        value={String(cardsTracked)}
      />
      <KpiCard
        title={t("marketPage.summary.avgPrice")}
        value={formatCurrency(avgPrice, currency)}
        icon={<CurrencyIndicator currency={currency} size={16} />}
      />
      <KpiCard
        title={t("marketPage.summary.avgChange")}
        value={changeFormatted}
        subtitle={
          <span className={changeColor}>
            {avgChange != null && avgChange > 0 ? "\u2191" : avgChange != null && avgChange < 0 ? "\u2193" : ""}
          </span>
        }
      />
      <KpiCard
        title={t("marketPage.summary.sentiment")}
        value={
          <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${directionColor}`}>
            {directionLabel}
          </span>
        }
      />
      <KpiCard
        title={t("marketPage.summary.gainersRatio")}
        value={`${gainersRatio}%`}
        subtitle={t("marketPage.direction.up").toLowerCase()}
      />
    </div>
  );
}
