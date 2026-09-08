import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { exportPnlCsv, fetchPortfolioHistory, fetchPortfolioSummary } from "../api/collection";
import type { PortfolioHistoryPoint, PortfolioSummary } from "../types/api";
import { formatCurrency } from "../utils/format";
import { CollectionMovers } from "./CollectionMovers";
import { KpiCard } from "./KpiCard";

const STORAGE_KEY = "portfolio_dashboard_visible";

function formatChartDate(dateStr: string): string {
  const [, month, day] = dateStr.slice(0, 10).split("-");
  return `${day}/${month}`;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
  }>;
  label?: string;
}

function PortfolioTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-md bg-slate-900 border border-slate-500 p-3 shadow-lg">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-sm text-cyan-400 font-semibold">
        {formatCurrency(payload[0].value, "BRL")}
      </p>
    </div>
  );
}

export function PortfolioDashboard() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored !== "false";
  });
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [history, setHistory] = useState<PortfolioHistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!visible) return;
    setLoading(true);
    Promise.all([
      fetchPortfolioSummary(),
      fetchPortfolioHistory(90),
    ])
      .then(([summaryRes, historyRes]) => {
        if (summaryRes.data) setSummary(summaryRes.data);
        if (historyRes.data) setHistory(historyRes.data);
      })
      .finally(() => setLoading(false));
  }, [visible]);

  const toggleVisible = useCallback(() => {
    setVisible((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const handleExport = useCallback(() => {
    exportPnlCsv();
  }, []);

  const pnlColor =
    summary && summary.total_pnl >= 0 ? "text-emerald-400" : "text-red-400";
  const pnlSign = summary && summary.total_pnl >= 0 ? "+" : "";

  return (
    <div className="mb-6" data-testid="portfolio-dashboard">
      {/* Toggle header */}
      <button
        type="button"
        onClick={toggleVisible}
        className="flex items-center gap-2 mb-3 text-sm font-medium text-slate-400 hover:text-cyan-400 transition-colors"
        data-testid="portfolio-toggle"
      >
        <svg
          className={`h-4 w-4 transition-transform ${visible ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        {t("portfolio.title")}
      </button>

      {visible && (
        <>
          {loading && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="animate-pulse bg-slate-700/50 rounded-lg h-24" />
              ))}
            </div>
          )}

          {!loading && summary && summary.invested_card_count > 0 && (
            <>
              {/* KPI cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <KpiCard
                  title={t("portfolio.totalInvested")}
                  value={formatCurrency(summary.total_invested, "BRL")}
                />
                <KpiCard
                  title={t("portfolio.currentValue")}
                  value={formatCurrency(summary.total_current_value, "BRL")}
                />
                <KpiCard
                  title={t("portfolio.totalPnl")}
                  value={
                    <span className={pnlColor}>
                      {pnlSign}{formatCurrency(summary.total_pnl, "BRL")}
                    </span>
                  }
                />
                <KpiCard
                  title={t("portfolio.pnlPct")}
                  value={
                    summary.total_pnl_pct != null ? (
                      <span className={pnlColor}>
                        {pnlSign}{summary.total_pnl_pct.toFixed(2)}%
                      </span>
                    ) : (
                      "--"
                    )
                  }
                />
              </div>

              {/* Portfolio value chart */}
              {history.length > 1 && (
                <div
                  className="bg-slate-800 rounded-lg p-4 border border-slate-600 mb-4"
                  data-testid="portfolio-chart"
                >
                  <h3 className="text-sm font-medium text-slate-400 mb-3">
                    {t("portfolio.valueOverTime")}
                  </h3>
                  <div className="w-full h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={history}>
                        <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
                        <XAxis
                          dataKey="date"
                          tickFormatter={formatChartDate}
                          stroke="#556275"
                          tick={{ fill: "#8494a7", fontSize: 12 }}
                        />
                        <YAxis
                          stroke="#556275"
                          tick={{ fill: "#8494a7", fontSize: 12 }}
                          tickFormatter={(v: number) => formatCurrency(v, "BRL")}
                        />
                        <Tooltip content={<PortfolioTooltip />} />
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#22d3ee"
                          strokeWidth={2}
                          dot={false}
                          connectNulls
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {history.length <= 1 && (
                <div
                  className="bg-slate-800/50 border border-dashed border-slate-600 rounded-lg p-6 text-center mb-4"
                  data-testid="portfolio-no-history"
                >
                  <p className="text-sm text-slate-400">
                    {t("portfolio.noHistory")}
                  </p>
                </div>
              )}

              {/* Collection movers */}
              <div className="mb-4">
                <CollectionMovers />
              </div>

              {/* Export button */}
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleExport}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
                    bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg
                    transition-colors duration-200"
                  data-testid="export-pnl-btn"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  {t("portfolio.exportPnl")}
                </button>
              </div>
            </>
          )}

          {!loading && summary && summary.invested_card_count === 0 && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 text-center">
              <p className="text-sm text-slate-400">
                {t("portfolio.noInvestmentData")}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
