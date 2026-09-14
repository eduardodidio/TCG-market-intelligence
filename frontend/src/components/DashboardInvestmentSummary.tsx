import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { fetchPortfolioSummary } from "../api/collection";
import { useApi } from "../hooks/useApi";
import type { PortfolioSummary } from "../types/api";
import { formatCurrency } from "../utils/format";
import { CurrencyIndicator } from "./CurrencyIndicator";
import { KpiCard } from "./KpiCard";
import { SkeletonKpi } from "./Skeleton";

interface DashboardInvestmentSummaryProps {
  totalUnique: number;
}

export function DashboardInvestmentSummary({ totalUnique }: DashboardInvestmentSummaryProps) {
  const { t } = useTranslation();
  const { data, loading, error } = useApi<PortfolioSummary>(() => fetchPortfolioSummary());

  if (loading) {
    return (
      <div data-testid="dashboard-investment">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SkeletonKpi />
          <SkeletonKpi />
          <SkeletonKpi />
          <SkeletonKpi />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div data-testid="dashboard-investment">
        <div
          data-testid="dashboard-investment-error"
          className="rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 p-6 text-sm text-red-400"
        >
          {t("dashboard.investmentError")}
        </div>
      </div>
    );
  }

  if (data.invested_card_count === 0) {
    return (
      <div data-testid="dashboard-investment">
        <div
          data-testid="dashboard-investment-empty"
          className="rounded-lg bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 p-6 text-center"
        >
          <p className="text-base font-semibold text-gray-900 dark:text-white">
            {t("dashboard.investmentEmptyTitle")}
          </p>
          <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
            {t("dashboard.investmentEmptyDesc")}
          </p>
          <Link
            to="/collection"
            className="mt-4 inline-block rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 transition-colors"
          >
            {t("dashboard.investmentEmptyCta")}
          </Link>
        </div>
      </div>
    );
  }

  const pnlColor =
    data.total_pnl > 0
      ? "text-emerald-400"
      : data.total_pnl < 0
        ? "text-red-400"
        : "text-gray-500 dark:text-slate-400";
  const pnlSign = data.total_pnl > 0 ? "+" : "";
  const pct = totalUnique > 0
    ? Math.min(100, Math.round((data.invested_card_count / totalUnique) * 100))
    : 0;

  return (
    <div data-testid="dashboard-investment">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-medium text-gray-500 dark:text-slate-400">
          {t("dashboard.investmentTitle")}
        </h3>
        <CurrencyIndicator currency="BRL" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          title={t("portfolio.totalInvested")}
          value={formatCurrency(data.total_invested, "BRL")}
        />
        <KpiCard
          title={t("portfolio.currentValue")}
          value={formatCurrency(data.total_current_value, "BRL")}
        />
        <KpiCard
          title={t("portfolio.totalPnl")}
          value={
            <span className={pnlColor}>
              {pnlSign}
              {formatCurrency(data.total_pnl, "BRL")}
            </span>
          }
        />
        <KpiCard
          title={t("portfolio.pnlPct")}
          value={
            data.total_pnl_pct != null ? (
              <span className={pnlColor}>
                {pnlSign}
                {data.total_pnl_pct.toFixed(2)}%
              </span>
            ) : (
              "—"
            )
          }
        />
      </div>
      <div className="mt-3">
        <div
          data-testid="dashboard-investment-progress"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          className="h-2 w-full rounded-full bg-gray-200 dark:bg-white/10 overflow-hidden"
        >
          <div
            className="h-full rounded-full bg-indigo-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
          {t("dashboard.investmentProgress", {
            count: data.invested_card_count,
            total: totalUnique,
          })}
        </p>
        {!!data.unpriced_card_count && data.unpriced_card_count > 0 && (
          <p
            data-testid="dashboard-investment-unpriced"
            className="mt-1 text-xs text-amber-500 dark:text-amber-400"
          >
            {t("dashboard.investmentUnpriced", { count: data.unpriced_card_count })}
          </p>
        )}
      </div>
    </div>
  );
}
