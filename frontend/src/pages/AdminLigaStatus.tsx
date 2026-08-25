import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { apiGet } from "../api/client";
import { triggerScanAuth, getScanStatusAuth } from "../api/scans";
import { useApi } from "../hooks/useApi";
import type {
  ApiResponse,
  CollectionCard,
  LigaStatusResponse,
  ScanTriggerResponse,
  ScanRun,
} from "../types/api";

function KpiCard({
  label,
  value,
  accent = "cyan",
}: {
  label: string;
  value: number | string;
  accent?: string;
}) {
  const colorMap: Record<string, string> = {
    cyan: "text-cyan-400",
    green: "text-green-400",
    amber: "text-amber-400",
    red: "text-red-400",
  };
  return (
    <div
      className="bg-slate-800 rounded-lg p-4 border border-slate-700"
      data-testid={`kpi-${label.toLowerCase().replace(/[^a-z]/g, "-")}`}
    >
      <p className="text-sm text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colorMap[accent] || "text-white"}`}>
        {value}
      </p>
    </div>
  );
}

function CoverageBar({ pct }: { pct: number }) {
  const clampedPct = Math.min(100, Math.max(0, pct));
  const barColor =
    clampedPct >= 80
      ? "bg-green-500"
      : clampedPct >= 50
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div data-testid="coverage-bar">
      <div className="flex justify-between text-sm text-slate-400 mb-1">
        <span>Liga Coverage</span>
        <span>{clampedPct.toFixed(1)}%</span>
      </div>
      <div className="w-full bg-slate-700 rounded-full h-3">
        <div
          className={`${barColor} h-3 rounded-full transition-all duration-500`}
          style={{ width: `${clampedPct}%` }}
          role="progressbar"
          aria-valuenow={clampedPct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}

export function AdminLigaStatus() {
  const { t } = useTranslation();
  const [scanRunning, setScanRunning] = useState(false);
  const [scanId, setScanId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    document.title = `${t("admin.ligaStatus.title")} | TCG Market`;
  }, [t]);

  const statusFetcher = useCallback(
    (signal: AbortSignal) =>
      apiGet<LigaStatusResponse>("/api/v1/collection/liga-status", undefined, {
        signal,
      }),
    [],
  );
  const status = useApi<LigaStatusResponse>(statusFetcher, []);

  const [missingCards, setMissingCards] = useState<CollectionCard[]>([]);
  const [missingTotal, setMissingTotal] = useState(0);
  const [missingOffset, setMissingOffset] = useState(0);
  const [missingLoading, setMissingLoading] = useState(true);
  const LIMIT = 50;

  const fetchMissing = useCallback(
    async (offset: number) => {
      setMissingLoading(true);
      const resp = await apiGet<CollectionCard[]>(
        "/api/v1/collection/liga-missing",
        {
          offset: String(offset),
          limit: String(LIMIT),
        },
      );
      if (resp.data) {
        setMissingCards(resp.data);
        setMissingTotal(resp.meta.total ?? 0);
      }
      setMissingLoading(false);
    },
    [],
  );

  useEffect(() => {
    fetchMissing(missingOffset);
  }, [missingOffset, fetchMissing]);

  // Auto-refresh when scan is running
  useEffect(() => {
    if (scanRunning && scanId !== null) {
      pollRef.current = setInterval(async () => {
        const resp: ApiResponse<ScanRun> = await getScanStatusAuth(scanId);
        if (
          resp.data &&
          (resp.data.status === "completed" || resp.data.status === "failed")
        ) {
          setScanRunning(false);
          setScanId(null);
          status.refetch();
          fetchMissing(0);
          setMissingOffset(0);
        }
      }, 3000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [scanRunning, scanId, status, fetchMissing]);

  const handleScanAll = async () => {
    setScanRunning(true);
    const resp: ApiResponse<ScanTriggerResponse> = await triggerScanAuth({
      scan_type: "collection",
      provider: "liga",
    });
    if (resp.data) {
      setScanId(resp.data.scan_id);
    } else {
      setScanRunning(false);
    }
  };

  const hasNextPage = missingOffset + LIMIT < missingTotal;
  const hasPrevPage = missingOffset > 0;

  return (
    <div data-testid="page-admin-liga-status">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <h1 className="text-2xl font-bold text-white">
          {t("admin.ligaStatus.title")}
        </h1>
        <button
          onClick={handleScanAll}
          disabled={scanRunning}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
          data-testid="scan-all-missing"
        >
          {scanRunning
            ? t("common.pleaseWait")
            : t("admin.ligaStatus.scanAllMissing")}
        </button>
      </div>

      {/* KPI Cards */}
      {status.loading ? (
        <p className="text-slate-400">{t("common.loading")}</p>
      ) : status.data ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard
              label={t("admin.ligaStatus.totalCards")}
              value={status.data.total_cards}
              accent="cyan"
            />
            <KpiCard
              label={t("admin.ligaStatus.ligaPriced")}
              value={status.data.liga_priced}
              accent="green"
            />
            <KpiCard
              label={t("admin.ligaStatus.ligaMissing")}
              value={status.data.liga_missing}
              accent="red"
            />
            <KpiCard
              label={t("admin.ligaStatus.ligaStale")}
              value={status.data.liga_stale}
              accent="amber"
            />
          </div>

          <div className="mb-6">
            <CoverageBar pct={status.data.coverage_pct} />
          </div>

          {status.data.last_liga_scan && (
            <p className="text-xs text-slate-500 mb-6">
              {t("admin.ligaStatus.lastScan")}: {status.data.last_liga_scan}
            </p>
          )}

          {status.data.unlinked > 0 && (
            <p className="text-xs text-amber-400 mb-4">
              {t("admin.ligaStatus.unlinked")}: {status.data.unlinked}
            </p>
          )}
        </>
      ) : null}

      {/* Missing cards table */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">
            {t("admin.ligaStatus.ligaMissing")} ({missingTotal})
          </h2>
        </div>
        {missingLoading ? (
          <p className="p-4 text-slate-400">{t("common.loading")}</p>
        ) : missingCards.length === 0 ? (
          <p className="p-4 text-green-400" data-testid="no-missing">
            {t("admin.ligaStatus.noMissing")}
          </p>
        ) : (
          <>
            <table
              className="w-full text-sm text-left"
              data-testid="missing-table"
            >
              <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
                <tr>
                  <th className="px-4 py-2">Name</th>
                  <th className="px-4 py-2">Set</th>
                  <th className="px-4 py-2">#</th>
                  <th className="px-4 py-2">Qty</th>
                </tr>
              </thead>
              <tbody>
                {missingCards.map((card) => (
                  <tr
                    key={card.id}
                    className="border-t border-slate-700 hover:bg-slate-700/50"
                  >
                    <td className="px-4 py-2 text-white">
                      {card.name_en || card.name_pt || "Unknown"}
                    </td>
                    <td className="px-4 py-2 text-slate-400 uppercase">
                      {card.set_code}
                    </td>
                    <td className="px-4 py-2 text-slate-400">
                      {card.collector_number}
                    </td>
                    <td className="px-4 py-2 text-slate-400">
                      {card.quantity}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
              <span className="text-xs text-slate-400">
                {missingOffset + 1}--
                {Math.min(missingOffset + LIMIT, missingTotal)} of{" "}
                {missingTotal}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={!hasPrevPage}
                  onClick={() => setMissingOffset(Math.max(0, missingOffset - LIMIT))}
                  className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                >
                  Prev
                </button>
                <button
                  disabled={!hasNextPage}
                  onClick={() => setMissingOffset(missingOffset + LIMIT)}
                  className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
