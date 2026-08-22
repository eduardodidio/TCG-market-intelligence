import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Brush,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
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
import type { ApiResponse, PriceHistoryResponse, PriceObservation } from "../types/api";

export interface PriceChartProps {
  cardId: number;
  currency?: string;
  period?: string;
  onPeriodChange?: (period: string) => void;
  fetchHistory?: (period: string, currency: string) => Promise<ApiResponse<PriceHistoryResponse>>;
}

const PERIODS = [
  { labelKey: "chart.period24h", value: "24h" },
  { labelKey: "chart.period7d", value: "7d" },
  { labelKey: "chart.period30d", value: "30d" },
  { labelKey: "chart.period90d", value: "90d" },
  { labelKey: "chart.period180d", value: "180d" },
  { labelKey: "chart.period1y", value: "1y" },
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
    <div className="rounded-md bg-slate-900 border border-slate-500 p-3 shadow-lg">
      <p className="text-xs text-slate-400 mb-2">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {formatCurrency(entry.value, currency)}
        </p>
      ))}
      {quantity != null && (
        <p className="text-xs text-slate-400 mt-1">
          {`Qty available: ${quantity}`}
        </p>
      )}
    </div>
  );
}

function isHistoryResponse(data: unknown): data is PriceHistoryResponse {
  return data != null && typeof data === "object" && "observations" in data;
}

interface ZoomState {
  left: string | null;
  right: string | null;
}

export function PriceChart({
  cardId,
  currency = "BRL",
  period: externalPeriod,
  onPeriodChange,
  fetchHistory,
}: PriceChartProps) {
  const { t } = useTranslation();
  const [internalPeriod, setInternalPeriod] = useState("30d");
  const period = externalPeriod ?? internalPeriod;
  const setPeriod = (p: string) => {
    if (onPeriodChange) {
      onPeriodChange(p);
    } else {
      setInternalPeriod(p);
    }
  };
  const [zoom, setZoom] = useState<ZoomState>({ left: null, right: null });
  const [refAreaLeft, setRefAreaLeft] = useState<string | null>(null);
  const [refAreaRight, setRefAreaRight] = useState<string | null>(null);
  const isDragging = useRef(false);

  const historyFetcher = useCallback(
    () => {
      if (fetchHistory) {
        return fetchHistory(period, currency);
      }
      return fetchCardHistory(cardId, period, currency);
    },
    [cardId, period, currency, fetchHistory],
  );

  const { data: rawData, loading, error, refetch } = useApi<PriceHistoryResponse | PriceObservation[]>(
    historyFetcher as (signal: AbortSignal) => Promise<ApiResponse<PriceHistoryResponse | PriceObservation[]>>,
    [cardId, period, currency, fetchHistory],
  );

  // Normalize response: support both new {observations, summary} and legacy PriceObservation[]
  let observations: PriceObservation[] = [];
  let summary: PriceHistoryResponse["summary"] = null;
  if (rawData) {
    if (isHistoryResponse(rawData)) {
      observations = rawData.observations;
      summary = rawData.summary;
    } else if (Array.isArray(rawData)) {
      observations = rawData;
    }
  }

  const isZoomed = zoom.left !== null && zoom.right !== null;

  function getZoomedData(data: PriceObservation[]): PriceObservation[] {
    if (!isZoomed) return data;
    const leftIdx = data.findIndex((d) => d.observed_at === zoom.left);
    const rightIdx = data.findIndex((d) => d.observed_at === zoom.right);
    if (leftIdx === -1 || rightIdx === -1) return data;
    const start = Math.min(leftIdx, rightIdx);
    const end = Math.max(leftIdx, rightIdx);
    return data.slice(start, end + 1);
  }

  function handleMouseDown(e: { activeLabel?: string }) {
    if (e?.activeLabel) {
      setRefAreaLeft(e.activeLabel);
      setRefAreaRight(null);
      isDragging.current = true;
    }
  }

  function handleMouseMove(e: { activeLabel?: string }) {
    if (isDragging.current && refAreaLeft && e?.activeLabel) {
      setRefAreaRight(e.activeLabel);
    }
  }

  function handleMouseUp() {
    if (!isDragging.current) return;
    isDragging.current = false;

    if (refAreaLeft && refAreaRight && refAreaLeft !== refAreaRight) {
      const data = observations;
      const leftIdx = data.findIndex((d) => d.observed_at === refAreaLeft);
      const rightIdx = data.findIndex((d) => d.observed_at === refAreaRight);
      if (leftIdx !== -1 && rightIdx !== -1) {
        const startIdx = Math.min(leftIdx, rightIdx);
        const endIdx = Math.max(leftIdx, rightIdx);
        setZoom({
          left: data[startIdx].observed_at,
          right: data[endIdx].observed_at,
        });
      }
    }
    setRefAreaLeft(null);
    setRefAreaRight(null);
  }

  function resetZoom() {
    setZoom({ left: null, right: null });
    setRefAreaLeft(null);
    setRefAreaRight(null);
    isDragging.current = false;
  }

  function getChangeColor(value: number | null | undefined): string {
    if (value == null || value === 0) return "text-slate-400";
    return value > 0 ? "text-green-400" : "text-red-400";
  }

  function formatChange(abs: number | null | undefined, pct: number | null | undefined, curr: string): string {
    if (abs == null || pct == null) return "--";
    const sign = abs >= 0 ? "+" : "";
    return `${sign}${formatCurrency(abs, curr)} (${sign}${pct.toFixed(1)}%)`;
  }

  return (
    <div data-testid="price-chart" className="bg-slate-800 rounded-lg p-4 border border-slate-600">
      {/* Period selector + zoom reset */}
      <div className="flex items-center justify-between mb-4">
        <div data-testid="period-selector" className="flex gap-2 flex-wrap">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              data-testid={`period-btn-${p.value}`}
              onClick={() => {
                setPeriod(p.value);
                resetZoom();
              }}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                period === p.value
                  ? "bg-indigo-500 text-white shadow-md"
                  : "bg-slate-700 text-slate-400 hover:text-white hover:bg-slate-600"
              }`}
            >
              {t(p.labelKey)}
            </button>
          ))}
        </div>

        {isZoomed && (
          <button
            data-testid="reset-zoom-btn"
            onClick={resetZoom}
            className="px-3 py-1.5 rounded-md text-sm font-medium bg-amber-400 text-slate-900 hover:brightness-110 transition-colors"
          >
            {t("chart.resetZoom")}
          </button>
        )}
      </div>

      {/* Price change summary */}
      {!loading && !error && summary && summary.price_start != null && summary.price_end != null && (
        <div data-testid="price-summary" className="flex flex-wrap items-center gap-4 mb-4 text-sm">
          <span className="text-slate-400">
            {t("chart.priceStart")}: <span className="text-white font-medium">{formatCurrency(summary.price_start, currency)}</span>
          </span>
          <span className="text-slate-400">
            {t("chart.priceEnd")}: <span className="text-white font-medium">{formatCurrency(summary.price_end, currency)}</span>
          </span>
          <span className={getChangeColor(summary.absolute_change)}>
            {t("chart.priceChange")}: {formatChange(summary.absolute_change, summary.percent_change, currency)}
          </span>
          <span
            data-testid="resolution-badge"
            className="rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-400"
          >
            {summary.resolution === "weekly" ? t("chart.resolutionWeekly") : t("chart.resolutionDaily")}
          </span>
        </div>
      )}

      {/* No data for period message */}
      {!loading && !error && summary && summary.price_start == null && summary.price_end == null && observations.length === 0 && (
        <p data-testid="no-data-for-period" className="text-slate-400 text-sm mb-3">
          {t("chart.noDataForPeriod")}
        </p>
      )}

      {/* Chart area */}
      {loading && <LoadingSpinner message={t("chart.loadingHistory")} />}

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {!loading && !error && observations.length === 0 && (
        <p data-testid="empty-history" className="text-slate-400 text-center py-8">
          {t("chart.noHistory")}
        </p>
      )}

      {!loading && !error && observations.length > 0 && (() => {
        const isSparse = observations.length < 7;
        const displayData = getZoomedData(observations);
        return (
          <>
            {isSparse && (
              <p data-testid="sparse-data-notice" className="text-sm text-amber-400/80 mb-3">
                {t("chart.sparseData", { count: observations.length })}
              </p>
            )}
            <div data-testid="chart-container" className="w-full h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={displayData}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                >
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="observed_at"
                    tickFormatter={formatChartDate}
                    stroke="#556275"
                    tick={{ fill: "#8494a7", fontSize: 12 }}
                  />
                  <YAxis
                    stroke="#556275"
                    tick={{ fill: "#8494a7", fontSize: 12 }}
                    tickFormatter={(v: number) => formatCurrency(v, currency)}
                    domain={[0, (dataMax: number) => Math.ceil(dataMax * 1.1)]}
                  />
                  <Tooltip
                    content={<ChartTooltip currency={currency} />}
                    cursor={{ strokeDasharray: "3 3" }}
                  />
                  <Legend
                    wrapperStyle={{ color: "#e2e8f0" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="median_price"
                    name={t("chart.median")}
                    stroke="#22d3ee"
                    strokeWidth={2}
                    dot={isSparse ? { r: 3, fill: "#22d3ee" } : false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="tcg_price"
                    name={t("chart.tcg")}
                    stroke="#8494a7"
                    strokeWidth={1.5}
                    strokeDasharray="5 5"
                    dot={isSparse ? { r: 3, fill: "#8494a7" } : false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="last_sold_price"
                    name={t("chart.lastSold")}
                    stroke="#4ade80"
                    strokeWidth={1.5}
                    strokeDasharray="2 2"
                    dot={isSparse ? { r: 3, fill: "#4ade80" } : false}
                    connectNulls
                  />
                  {!isZoomed && observations.length > 14 && (
                    <Brush
                      dataKey="observed_at"
                      height={30}
                      stroke="#6366f1"
                      fill="#12161e"
                      tickFormatter={formatChartDate}
                    />
                  )}
                  {refAreaLeft && refAreaRight && (
                    <ReferenceArea
                      x1={refAreaLeft}
                      x2={refAreaRight}
                      strokeOpacity={0.3}
                      fill="#6366f1"
                      fillOpacity={0.15}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        );
      })()}
    </div>
  );
}
