import { useCallback, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useApi } from "../hooks/useApi";
import { fetchCardHistory } from "../api/cards";
import { formatCurrency } from "../utils/format";
import { LoadingSpinner } from "./LoadingSpinner";
import { ErrorBanner } from "./ErrorBanner";
import type { PriceObservation } from "../types/api";

interface PriceChartProps {
  cardId: number;
  currency?: string;
}

const PERIODS = [
  { label: "30d", value: "30d" },
  { label: "90d", value: "90d" },
  { label: "180d", value: "180d" },
  { label: "1y", value: "1y" },
  { label: "3y", value: "3y" },
] as const;

function formatChartDate(dateStr: string): string {
  const [, month, day] = dateStr.slice(0, 10).split("-");
  return `${day}/${month}`;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    dataKey: string;
    value: number | null;
    color: string;
    name: string;
  }>;
  label?: string;
}

function ChartTooltip({ active, payload, label, currency = "BRL" }: CustomTooltipProps & { currency?: string }) {
  if (!active || !payload || payload.length === 0) return null;

  // Find quantity from the original data point
  const dataPoint = payload[0] as unknown as {
    payload?: PriceObservation;
  };
  const quantity = dataPoint?.payload?.quantity_available;

  return (
    <div className="rounded-lg bg-slate-900 border border-slate-600 p-3 shadow-lg">
      <p className="text-xs text-slate-400 mb-2">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {formatCurrency(entry.value, currency)}
        </p>
      ))}
      {quantity != null && (
        <p className="text-xs text-slate-400 mt-1">
          Qty available: {quantity}
        </p>
      )}
    </div>
  );
}

export function PriceChart({ cardId, currency = "BRL" }: PriceChartProps) {
  const [period, setPeriod] = useState("90d");

  const historyFetcher = useCallback(
    () => fetchCardHistory(cardId, period, currency),
    [cardId, period, currency],
  );

  const { data: observations, loading, error, refetch } = useApi<PriceObservation[]>(
    historyFetcher,
    [cardId, period, currency],
  );

  return (
    <div data-testid="price-chart" className="bg-slate-800 rounded-xl p-4">
      {/* Period selector */}
      <div data-testid="period-selector" className="flex gap-2 mb-4">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            data-testid={`period-btn-${p.value}`}
            onClick={() => setPeriod(p.value)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              period === p.value
                ? "bg-cyan-500 text-white"
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Chart area */}
      {loading && <LoadingSpinner message="Loading price history..." />}

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {!loading && !error && (!observations || observations.length === 0) && (
        <p data-testid="empty-history" className="text-slate-400 text-center py-8">
          No price history available
        </p>
      )}

      {!loading && !error && observations && observations.length > 0 && (() => {
        const isSparse = observations.length < 7;
        return (
          <>
            {isSparse && (
              <p data-testid="sparse-data-notice" className="text-sm text-amber-400/80 mb-3">
                Building price history -- {observations.length} data point{observations.length !== 1 ? 's' : ''} so far.
                Daily snapshots will fill this chart over time.
              </p>
            )}
            <div data-testid="chart-container" className="w-full h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={observations}>
                  <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="observed_at"
                    tickFormatter={formatChartDate}
                    stroke="#94a3b8"
                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                  />
                  <YAxis
                    stroke="#94a3b8"
                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                    tickFormatter={(v: number) => formatCurrency(v, currency)}
                  />
                  <Tooltip content={<ChartTooltip currency={currency} />} />
                  <Legend
                    wrapperStyle={{ color: "#e2e8f0" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="median_price"
                    name="Median"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    dot={isSparse ? { r: 3, fill: "#06b6d4" } : false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="tcg_price"
                    name="TCG"
                    stroke="#94a3b8"
                    strokeWidth={1.5}
                    strokeDasharray="5 5"
                    dot={isSparse ? { r: 3, fill: "#94a3b8" } : false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="last_sold_price"
                    name="Last Sold"
                    stroke="#4ade80"
                    strokeWidth={1.5}
                    strokeDasharray="2 2"
                    dot={isSparse ? { r: 3, fill: "#4ade80" } : false}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        );
      })()}
    </div>
  );
}
