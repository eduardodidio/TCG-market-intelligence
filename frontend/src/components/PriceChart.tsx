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
    <div className="rounded-tcg-md bg-tcg-bg border border-tcg-ring p-3 shadow-tcg-lg">
      <p className="text-xs text-tcg-muted mb-2">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="text-sm" style={{ color: entry.color }}>
          {entry.name}: {formatCurrency(entry.value, currency)}
        </p>
      ))}
      {quantity != null && (
        <p className="text-xs text-tcg-muted mt-1">
          {`Qty available: ${quantity}`}
        </p>
      )}
    </div>
  );
}

interface ZoomState {
  left: string | null;
  right: string | null;
}

export function PriceChart({ cardId, currency = "BRL" }: PriceChartProps) {
  const { t } = useTranslation();
  const [period, setPeriod] = useState("90d");
  const [zoom, setZoom] = useState<ZoomState>({ left: null, right: null });
  const [refAreaLeft, setRefAreaLeft] = useState<string | null>(null);
  const [refAreaRight, setRefAreaRight] = useState<string | null>(null);
  const isDragging = useRef(false);

  const historyFetcher = useCallback(
    () => fetchCardHistory(cardId, period, currency),
    [cardId, period, currency],
  );

  const { data: observations, loading, error, refetch } = useApi<PriceObservation[]>(
    historyFetcher,
    [cardId, period, currency],
  );

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
      // Ensure left < right
      const data = observations ?? [];
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

  return (
    <div data-testid="price-chart" className="bg-tcg-card rounded-tcg-lg p-4 border border-tcg-border">
      {/* Period selector + zoom reset */}
      <div className="flex items-center justify-between mb-4">
        <div data-testid="period-selector" className="flex gap-2">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              data-testid={`period-btn-${p.value}`}
              onClick={() => {
                setPeriod(p.value);
                resetZoom();
              }}
              className={`px-3 py-1.5 rounded-tcg-md text-sm font-medium transition-colors ${
                period === p.value
                  ? "bg-tcg-primary text-white shadow-tcg-glow"
                  : "bg-tcg-card-alt text-tcg-muted hover:text-white hover:bg-tcg-ring"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {isZoomed && (
          <button
            data-testid="reset-zoom-btn"
            onClick={resetZoom}
            className="px-3 py-1.5 rounded-tcg-md text-sm font-medium bg-tcg-warning text-tcg-bg hover:brightness-110 transition-colors"
          >
            {t("chart.resetZoom")}
          </button>
        )}
      </div>

      {/* Chart area */}
      {loading && <LoadingSpinner message={t("chart.loadingHistory")} />}

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {!loading && !error && (!observations || observations.length === 0) && (
        <p data-testid="empty-history" className="text-tcg-muted text-center py-8">
          {t("chart.noHistory")}
        </p>
      )}

      {!loading && !error && observations && observations.length > 0 && (() => {
        const isSparse = observations.length < 7;
        const displayData = getZoomedData(observations);
        return (
          <>
            {isSparse && (
              <p data-testid="sparse-data-notice" className="text-sm text-tcg-warning/80 mb-3">
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
