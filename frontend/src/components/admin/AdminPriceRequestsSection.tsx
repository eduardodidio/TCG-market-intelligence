import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  fetchAdminPriceRequests,
  fetchAdminPriceRequestStats,
  triggerProcessPriceRequests,
} from "../../api/admin";
import type { PriceRequest } from "../../api/admin";

const LIMIT = 50;

const STATUS_FILTERS = ["all", "pending", "processing", "completed", "failed"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-900 text-yellow-300",
    processing: "bg-blue-900 text-blue-300",
    completed: "bg-green-900 text-green-300",
    failed: "bg-red-900 text-red-300",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded ${colors[status] || "bg-slate-700 text-slate-300"}`}
      data-testid={`status-badge-${status}`}
    >
      {status}
    </span>
  );
}

function StatsBadge({
  label,
  count,
  colorClass,
}: {
  label: string;
  count: number;
  colorClass: string;
}) {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium ${colorClass}`}
      data-testid={`stats-badge-${label}`}
    >
      <span>{label}</span>
      <span className="font-bold">{count}</span>
    </div>
  );
}

function PriceRequestsContent() {
  const { t } = useTranslation();

  // Data state
  const [requests, setRequests] = useState<PriceRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  // Stats state
  const [stats, setStats] = useState<Record<string, number> | null>(null);

  // Processing state
  const [processing, setProcessing] = useState(false);
  const [processMessage, setProcessMessage] = useState<string | null>(null);

  // Filter state
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [offset, setOffset] = useState(0);

  const loadStats = useCallback(async () => {
    const resp = await fetchAdminPriceRequestStats();
    if (resp.data) {
      setStats(resp.data);
    }
  }, []);

  const loadRequests = useCallback(async () => {
    setLoading(true);
    const resp = await fetchAdminPriceRequests({
      status: statusFilter === "all" ? undefined : statusFilter,
      limit: LIMIT,
      offset,
    });
    if (resp.data) {
      setRequests(resp.data.items);
      setTotal(resp.data.total);
    } else {
      setRequests([]);
      setTotal(0);
    }
    setLoading(false);
  }, [statusFilter, offset]);

  const handleProcessQueue = useCallback(async () => {
    setProcessing(true);
    setProcessMessage(null);
    try {
      const resp = await triggerProcessPriceRequests();
      if (resp.data) {
        if (resp.data.status === "no_pending") {
          setProcessMessage(t("admin.priceRequests.noPending"));
        } else {
          setProcessMessage(t("admin.priceRequests.processingStarted"));
          // Refresh stats and list after a delay
          setTimeout(() => {
            loadStats();
            loadRequests();
          }, 5000);
        }
      }
    } catch {
      setProcessMessage(t("cards.priceRefreshError"));
    } finally {
      setProcessing(false);
    }
  }, [t, loadStats, loadRequests]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const handleFilterChange = (filter: StatusFilter) => {
    setStatusFilter(filter);
    setOffset(0);
  };

  const hasNextPage = offset + LIMIT < total;
  const hasPrevPage = offset > 0;

  return (
    <div data-testid="price-requests-section">
      {/* Process queue button */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={handleProcessQueue}
          disabled={processing || (stats?.pending ?? 0) === 0}
          className="px-4 py-2 text-sm bg-cyan-700 hover:bg-cyan-600
            disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg
            flex items-center gap-2 transition-colors"
          data-testid="process-queue-btn"
          title={t("admin.priceRequests.localOnly")}
        >
          {processing ? (
            <>
              <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {t("admin.priceRequests.processingRunning")}
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {t("admin.priceRequests.processQueuePending", { count: stats?.pending ?? 0 })}
            </>
          )}
        </button>
        {processMessage && (
          <span className="text-sm text-slate-300" data-testid="process-message">
            {processMessage}
          </span>
        )}
      </div>

      {/* Stats bar */}
      {stats && (
        <div
          className="flex flex-wrap gap-2 mb-4"
          data-testid="price-requests-stats"
        >
          <StatsBadge
            label={t("admin.priceRequests.pending")}
            count={stats.pending ?? 0}
            colorClass="bg-yellow-900/50 text-yellow-300"
          />
          <StatsBadge
            label={t("admin.priceRequests.processing")}
            count={stats.processing ?? 0}
            colorClass="bg-blue-900/50 text-blue-300"
          />
          <StatsBadge
            label={t("admin.priceRequests.completed")}
            count={stats.completed ?? 0}
            colorClass="bg-green-900/50 text-green-300"
          />
          <StatsBadge
            label={t("admin.priceRequests.failed")}
            count={stats.failed ?? 0}
            colorClass="bg-red-900/50 text-red-300"
          />
        </div>
      )}

      {/* Filter tabs */}
      <div
        className="flex flex-wrap gap-1 mb-4"
        data-testid="price-requests-filter-tabs"
      >
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter}
            onClick={() => handleFilterChange(filter)}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              statusFilter === filter
                ? "bg-cyan-700 text-white"
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
            data-testid={`filter-tab-${filter}`}
          >
            {filter === "all"
              ? t("admin.priceRequests.allFilter")
              : t(`admin.priceRequests.${filter}`)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        {loading ? (
          <p className="p-4 text-slate-400" data-testid="price-requests-loading">
            {t("common.loading")}
          </p>
        ) : requests.length === 0 ? (
          <p className="p-4 text-slate-400" data-testid="price-requests-empty">
            {t("admin.priceRequests.noRequests")}
          </p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table
                className="w-full text-sm text-left"
                data-testid="price-requests-table"
              >
                <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
                  <tr>
                    <th className="px-4 py-2">
                      {t("admin.priceRequests.colCardName")}
                    </th>
                    <th className="px-4 py-2">
                      {t("admin.priceRequests.colUserId")}
                    </th>
                    <th className="px-4 py-2">
                      {t("admin.priceRequests.colStatus")}
                    </th>
                    <th className="px-4 py-2">
                      {t("admin.priceRequests.colRequested")}
                    </th>
                    <th className="px-4 py-2">
                      {t("admin.priceRequests.colProcessed")}
                    </th>
                    <th className="px-4 py-2">
                      {t("admin.priceRequests.colPrice")}
                    </th>
                    <th className="px-4 py-2">
                      {t("admin.priceRequests.colError")}
                    </th>
                    <th className="px-4 py-2">
                      {t("admin.priceRequests.colAttempts")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map((req) => (
                    <PriceRequestRow key={req.id} request={req} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
              <span
                className="text-xs text-slate-400"
                data-testid="price-requests-pagination-info"
              >
                {offset + 1}--{Math.min(offset + LIMIT, total)}{" "}
                {t("common.of")} {total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={!hasPrevPage}
                  onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                  className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                  data-testid="price-requests-prev"
                >
                  {t("common.prev")}
                </button>
                <button
                  disabled={!hasNextPage}
                  onClick={() => setOffset(offset + LIMIT)}
                  className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                  data-testid="price-requests-next"
                >
                  {t("common.next")}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function PriceRequestRow({ request }: { request: PriceRequest }) {
  const requestedAt = new Date(request.requested_at).toLocaleString();
  const processedAt = request.processed_at
    ? new Date(request.processed_at).toLocaleString()
    : "--";
  const price =
    request.result_price !== null
      ? `R$ ${request.result_price.toFixed(2)}`
      : "--";
  const errorMsg = request.error_message
    ? request.error_message.length > 50
      ? request.error_message.slice(0, 50) + "..."
      : request.error_message
    : "--";

  return (
    <tr
      className="border-t border-slate-700 hover:bg-slate-700/50"
      data-testid={`price-request-row-${request.id}`}
    >
      <td className="px-4 py-2 text-white text-xs">{request.card_name}</td>
      <td className="px-4 py-2 text-slate-300 text-xs">{request.user_id}</td>
      <td className="px-4 py-2">
        <StatusBadge status={request.status} />
      </td>
      <td className="px-4 py-2 text-slate-300 text-xs whitespace-nowrap">
        {requestedAt}
      </td>
      <td className="px-4 py-2 text-slate-300 text-xs whitespace-nowrap">
        {processedAt}
      </td>
      <td className="px-4 py-2 text-white text-xs font-mono">{price}</td>
      <td
        className="px-4 py-2 text-slate-400 text-xs max-w-xs truncate"
        title={request.error_message || undefined}
      >
        {errorMsg}
      </td>
      <td className="px-4 py-2 text-slate-300 text-xs text-center">
        {request.attempts}
      </td>
    </tr>
  );
}

export function AdminPriceRequestsSection({ isOpen }: { isOpen: boolean }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (isOpen && !loaded) {
      setLoaded(true);
    }
  }, [isOpen, loaded]);

  if (!loaded) return null;

  return <PriceRequestsContent />;
}
