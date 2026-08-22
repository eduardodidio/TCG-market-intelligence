import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { fetchCardMetrics } from "../api/metrics";
import { formatCurrency } from "../utils/format";
import { ErrorBanner } from "./ErrorBanner";
import type { CardMetricsResponse } from "../types/api";

interface MetricsPanelProps {
  entryId: number;
  period: string;
  currency: string;
}

function SkeletonCard() {
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-4 animate-pulse">
      <div className="h-3 w-20 bg-slate-700 rounded mb-3" />
      <div className="h-6 w-24 bg-slate-700 rounded mb-2" />
      <div className="h-3 w-16 bg-slate-700 rounded" />
    </div>
  );
}

function TrendCard({
  momentum,
  currency: curr,
}: {
  momentum: CardMetricsResponse["momentum"];
  currency: string;
}) {
  const { t } = useTranslation();
  if (!momentum) return null;

  const { rate_of_change, trend_direction, period_days } = momentum;

  let arrowIcon: string;
  let colorClass: string;
  let trendLabel: string;

  if (trend_direction === "up") {
    arrowIcon = "\u2191"; // up arrow
    colorClass = "text-green-400";
    trendLabel = t("metrics.trendUp");
  } else if (trend_direction === "down") {
    arrowIcon = "\u2193"; // down arrow
    colorClass = "text-red-400";
    trendLabel = t("metrics.trendDown");
  } else {
    arrowIcon = "\u2192"; // right arrow
    colorClass = "text-slate-400";
    trendLabel = t("metrics.trendFlat");
  }

  const sign = rate_of_change >= 0 ? "+" : "";

  return (
    <div data-testid="metric-trend" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
      <p className="text-xs text-slate-400 mb-1">{t("metrics.trend")}</p>
      <div className="flex items-center gap-2">
        <span className={`text-2xl font-bold ${colorClass}`}>{arrowIcon}</span>
        <span className={`text-xl font-bold ${colorClass}`}>
          {sign}{rate_of_change.toFixed(1)}%
        </span>
      </div>
      <p className="text-xs text-slate-400 mt-1">
        {period_days}d {t("metrics.momentum").toLowerCase()} &middot; {trendLabel}
      </p>
    </div>
  );
}

function MovingAveragesCard({
  averages,
  currency: curr,
}: {
  averages: CardMetricsResponse["moving_averages"];
  currency: string;
}) {
  const { t } = useTranslation();
  if (!averages || averages.length === 0) return null;

  const ma7 = averages.find((a) => a.period === 7);
  const ma30 = averages.find((a) => a.period === 30);

  return (
    <div data-testid="metric-moving-averages" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
      <p className="text-xs text-slate-400 mb-1">{t("metrics.movingAverages")}</p>
      <div className="flex gap-4">
        {ma7 && (
          <div>
            <p className="text-xs text-slate-400">{t("metrics.ma7")}</p>
            <p className="text-lg font-bold text-white">{formatCurrency(ma7.value, curr)}</p>
          </div>
        )}
        {ma30 && (
          <div>
            <p className="text-xs text-slate-400">{t("metrics.ma30")}</p>
            <p className="text-lg font-bold text-white">{formatCurrency(ma30.value, curr)}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function AthAtlCard({
  extremes,
  currency: curr,
}: {
  extremes: CardMetricsResponse["extremes"];
  currency: string;
}) {
  const { t } = useTranslation();
  if (!extremes) return null;

  function shortDate(iso: string): string {
    const [year, month, day] = iso.slice(0, 10).split("-");
    return `${day}/${month}/${year.slice(2)}`;
  }

  return (
    <div data-testid="metric-ath-atl" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
      <p className="text-xs text-slate-400 mb-1">{t("metrics.athAtl")}</p>
      <div className="flex gap-4">
        <div>
          <p className="text-xs text-green-400">{t("metrics.allTimeHigh")}</p>
          <p className="text-lg font-bold text-white">{formatCurrency(extremes.ath_price, curr)}</p>
          <p className="text-xs text-slate-400">{shortDate(extremes.ath_date)}</p>
        </div>
        <div>
          <p className="text-xs text-red-400">{t("metrics.allTimeLow")}</p>
          <p className="text-lg font-bold text-white">{formatCurrency(extremes.atl_price, curr)}</p>
          <p className="text-xs text-slate-400">{shortDate(extremes.atl_date)}</p>
        </div>
      </div>
    </div>
  );
}

function VolatilityCard({
  volatility,
}: {
  volatility: CardMetricsResponse["volatility"];
}) {
  const { t } = useTranslation();
  if (!volatility) return null;

  const { coefficient_of_variation, period_days } = volatility;

  let barColor: string;
  let levelLabel: string;

  if (coefficient_of_variation < 0.1) {
    barColor = "bg-green-400";
    levelLabel = t("metrics.volatilityLow");
  } else if (coefficient_of_variation <= 0.3) {
    barColor = "bg-amber-400";
    levelLabel = t("metrics.volatilityMedium");
  } else {
    barColor = "bg-red-400";
    levelLabel = t("metrics.volatilityHigh");
  }

  const barWidth = Math.min(100, coefficient_of_variation * 200);

  return (
    <div data-testid="metric-volatility" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
      <p className="text-xs text-slate-400 mb-1">{t("metrics.volatility")}</p>
      <p className="text-xl font-bold text-white">{(coefficient_of_variation * 100).toFixed(1)}%</p>
      <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor}`}
          style={{ width: `${barWidth}%` }}
          data-testid="volatility-bar"
        />
      </div>
      <p className="text-xs text-slate-400 mt-1">
        {levelLabel} &middot; {period_days}d
      </p>
    </div>
  );
}

function PerformanceCard({
  performance,
}: {
  performance: CardMetricsResponse["performance"];
}) {
  const { t } = useTranslation();
  if (!performance) return null;

  const { score, label } = performance;

  const badgeColors: Record<string, string> = {
    strong: "bg-green-500/20 text-green-400",
    moderate: "bg-amber-500/20 text-amber-400",
    weak: "bg-slate-500/20 text-slate-400",
    declining: "bg-red-500/20 text-red-400",
  };

  const labelKeys: Record<string, string> = {
    strong: "metrics.performanceStrong",
    moderate: "metrics.performanceModerate",
    weak: "metrics.performanceWeak",
    declining: "metrics.performanceDeclining",
  };

  return (
    <div data-testid="metric-performance" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
      <p className="text-xs text-slate-400 mb-1">{t("metrics.performance")}</p>
      <p className="text-3xl font-bold text-white">{score}</p>
      <span
        data-testid="performance-badge"
        className={`inline-block mt-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeColors[label] ?? "bg-slate-500/20 text-slate-400"}`}
      >
        {t(labelKeys[label] ?? "metrics.notAvailable")}
      </span>
    </div>
  );
}

function PeriodComparisonCard({
  comparison,
  currency: curr,
  period,
}: {
  comparison: CardMetricsResponse["period_comparison"];
  currency: string;
  period: string;
}) {
  const { t } = useTranslation();
  if (!comparison) return null;

  const { current_avg, previous_avg, delta, delta_pct } = comparison;
  const isPositive = delta >= 0;
  const arrow = isPositive ? "\u2191" : "\u2193";
  const deltaColor = isPositive ? "text-green-400" : "text-red-400";
  const sign = isPositive ? "+" : "";

  return (
    <div data-testid="metric-period-comparison" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
      <p className="text-xs text-slate-400 mb-1">{t("metrics.periodComparison")}</p>
      <div className="flex gap-4">
        <div>
          <p className="text-xs text-slate-400">{t("metrics.currentPeriod")}</p>
          <p className="text-lg font-bold text-white">{formatCurrency(current_avg, curr)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400">{t("metrics.previousPeriod")}</p>
          <p className="text-lg font-bold text-white">{formatCurrency(previous_avg, curr)}</p>
        </div>
      </div>
      <p className={`text-sm mt-1 ${deltaColor}`}>
        {arrow} {sign}{formatCurrency(delta, curr)} ({sign}{delta_pct.toFixed(1)}%)
      </p>
      <p className="text-xs text-slate-400 mt-1">
        {t("metrics.vsPrevious", { period })}
      </p>
    </div>
  );
}

export function MetricsPanel({ entryId, period, currency }: MetricsPanelProps) {
  const { t } = useTranslation();

  const fetcher = useCallback(
    () => fetchCardMetrics(entryId, period, currency),
    [entryId, period, currency],
  );

  const { data: metrics, loading, error, refetch } = useApi<CardMetricsResponse>(
    fetcher,
    [entryId, period, currency],
  );

  if (loading) {
    return (
      <div data-testid="metrics-panel">
        <h3 className="text-lg font-bold text-white mb-3">{t("metrics.title")}</h3>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="metrics-panel">
        <h3 className="text-lg font-bold text-white mb-3">{t("metrics.title")}</h3>
        <ErrorBanner message={error} onRetry={refetch} />
      </div>
    );
  }

  if (!metrics || metrics.data_points === 0) {
    return (
      <div data-testid="metrics-panel">
        <h3 className="text-lg font-bold text-white mb-3">{t("metrics.title")}</h3>
        <p className="text-sm text-slate-400">{t("metrics.insufficientData")}</p>
      </div>
    );
  }

  return (
    <div data-testid="metrics-panel">
      <h3 className="text-lg font-bold text-white mb-3">{t("metrics.title")}</h3>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <TrendCard momentum={metrics.momentum} currency={currency} />
        <MovingAveragesCard averages={metrics.moving_averages} currency={currency} />
        <AthAtlCard extremes={metrics.extremes} currency={currency} />
        <VolatilityCard volatility={metrics.volatility} />
        <PerformanceCard performance={metrics.performance} />
        <PeriodComparisonCard comparison={metrics.period_comparison} currency={currency} period={period} />
      </div>
    </div>
  );
}
