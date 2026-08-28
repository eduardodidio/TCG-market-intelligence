import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  fetchAdminErrors,
  fetchAdminErrorDetail,
} from "../../api/admin";
import type { ErrorLogEntry, ErrorLogDetail } from "../../api/admin";

const LIMIT = 20;

function LevelBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    CRITICAL: "bg-red-900 text-red-300",
    ERROR: "bg-amber-900 text-amber-300",
    WARNING: "bg-yellow-900 text-yellow-300",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded ${colors[level] || "bg-slate-700 text-slate-300"}`}
      data-testid={`level-badge-${level}`}
    >
      {level}
    </span>
  );
}

function ErrorDetailView({ errorId }: { errorId: string }) {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<ErrorLogDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchAdminErrorDetail(errorId).then((resp) => {
      if (cancelled) return;
      if (resp.data) setDetail(resp.data);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [errorId]);

  if (loading) {
    return (
      <div className="p-4 text-slate-400" data-testid="error-detail-loading">
        {t("common.loading")}
      </div>
    );
  }

  if (!detail) return null;

  return (
    <div
      className="p-4 bg-slate-900 border-t border-slate-700 space-y-4"
      data-testid={`error-detail-${errorId}`}
    >
      {/* Traceback */}
      {detail.traceback && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase mb-1">
            {t("admin.errors.traceback")}
          </h4>
          <pre
            className="text-xs text-red-300 bg-slate-950 p-3 rounded overflow-x-auto max-h-64 overflow-y-auto font-mono"
            data-testid="error-traceback"
          >
            {detail.traceback}
          </pre>
        </div>
      )}

      {/* Line */}
      {detail.line !== null && (
        <p className="text-xs text-slate-400">
          {t("admin.errors.line")}: <span className="text-white">{detail.line}</span>
        </p>
      )}

      {/* Request context */}
      {(detail.request_method || detail.request_path) && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase mb-1">
            {t("admin.errors.requestContext")}
          </h4>
          <div className="text-xs bg-slate-950 p-3 rounded space-y-1">
            {detail.request_method && (
              <p className="text-slate-300">
                <span className="text-slate-500">Method:</span> {detail.request_method}
              </p>
            )}
            {detail.request_path && (
              <p className="text-slate-300">
                <span className="text-slate-500">Path:</span> {detail.request_path}
              </p>
            )}
            {detail.request_user_id !== null && (
              <p className="text-slate-300">
                <span className="text-slate-500">User ID:</span> {detail.request_user_id}
              </p>
            )}
            {detail.request_id && (
              <p className="text-slate-300">
                <span className="text-slate-500">Request ID:</span> {detail.request_id}
              </p>
            )}
            {detail.request_params && (
              <div>
                <p className="text-slate-500 mb-1">Params:</p>
                <pre className="text-slate-300 font-mono">
                  {JSON.stringify(detail.request_params, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Extra data */}
      {detail.extra && Object.keys(detail.extra).length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-slate-400 uppercase mb-1">
            {t("admin.errors.extra")}
          </h4>
          <pre
            className="text-xs text-slate-300 bg-slate-950 p-3 rounded overflow-x-auto font-mono"
            data-testid="error-extra"
          >
            {JSON.stringify(detail.extra, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function ErrorsContent() {
  const { t } = useTranslation();

  // Data state
  const [errors, setErrors] = useState<ErrorLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filter state
  const [levelFilter, setLevelFilter] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);

  const loadErrors = useCallback(async () => {
    setLoading(true);
    const resp = await fetchAdminErrors({
      level: levelFilter || undefined,
      module: moduleFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      limit: LIMIT,
      offset,
    });
    if (resp.data) {
      setErrors(resp.data);
      setTotal(resp.meta.total ?? resp.data.length);
    } else {
      setErrors([]);
      setTotal(0);
    }
    setLoading(false);
  }, [levelFilter, moduleFilter, dateFrom, dateTo, offset]);

  useEffect(() => {
    loadErrors();
  }, [loadErrors]);

  const handleFilterChange = () => {
    setOffset(0);
    // loadErrors will be called by the useEffect when offset/filters change
  };

  const hasNextPage = offset + LIMIT < total;
  const hasPrevPage = offset > 0;

  const handleRowClick = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div data-testid="errors-section">
      {/* Filter bar */}
      <div
        className="flex flex-wrap items-end gap-3 mb-4"
        data-testid="errors-filter-bar"
      >
        {/* Level filter */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            {t("admin.errors.level")}
          </label>
          <select
            value={levelFilter}
            onChange={(e) => {
              setLevelFilter(e.target.value);
              handleFilterChange();
            }}
            className="px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
            data-testid="errors-level-filter"
          >
            <option value="">{t("admin.errors.allLevels")}</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="ERROR">ERROR</option>
            <option value="WARNING">WARNING</option>
          </select>
        </div>

        {/* Module filter */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            {t("admin.errors.module")}
          </label>
          <input
            type="text"
            value={moduleFilter}
            onChange={(e) => {
              setModuleFilter(e.target.value);
              handleFilterChange();
            }}
            placeholder={t("admin.errors.module")}
            className="px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400 w-40"
            data-testid="errors-module-filter"
          />
        </div>

        {/* Date from */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            {t("admin.errors.dateFrom")}
          </label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              handleFilterChange();
            }}
            className="px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
            data-testid="errors-date-from"
          />
        </div>

        {/* Date to */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            {t("admin.errors.dateTo")}
          </label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              handleFilterChange();
            }}
            className="px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
            data-testid="errors-date-to"
          />
        </div>
      </div>

      {/* Content */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        {loading ? (
          <p className="p-4 text-slate-400" data-testid="errors-loading">
            {t("common.loading")}
          </p>
        ) : errors.length === 0 ? (
          <p className="p-4 text-slate-400" data-testid="errors-empty">
            {t("admin.errors.noErrors")}
          </p>
        ) : (
          <>
            <table
              className="w-full text-sm text-left"
              data-testid="errors-table"
            >
              <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
                <tr>
                  <th className="px-4 py-2">Timestamp</th>
                  <th className="px-4 py-2">{t("admin.errors.level")}</th>
                  <th className="px-4 py-2">{t("admin.errors.type")}</th>
                  <th className="px-4 py-2">{t("admin.errors.message")}</th>
                  <th className="px-4 py-2">{t("admin.errors.module")}</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((err) => (
                  <ErrorRow
                    key={err.id}
                    error={err}
                    isExpanded={expandedId === err.id}
                    onToggle={() => handleRowClick(err.id)}
                  />
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
              <span
                className="text-xs text-slate-400"
                data-testid="errors-pagination-info"
              >
                {offset + 1}--{Math.min(offset + LIMIT, total)} {t("common.of")}{" "}
                {total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={!hasPrevPage}
                  onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                  className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                  data-testid="errors-prev"
                >
                  {t("common.prev")}
                </button>
                <button
                  disabled={!hasNextPage}
                  onClick={() => setOffset(offset + LIMIT)}
                  className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                  data-testid="errors-next"
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

function ErrorRow({
  error,
  isExpanded,
  onToggle,
}: {
  error: ErrorLogEntry;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const ts = new Date(error.timestamp).toLocaleString();
  const truncatedMsg =
    error.message.length > 80
      ? error.message.slice(0, 80) + "..."
      : error.message;

  return (
    <>
      <tr
        className="border-t border-slate-700 hover:bg-slate-700/50 cursor-pointer"
        onClick={onToggle}
        data-testid={`error-row-${error.id}`}
      >
        <td className="px-4 py-2 text-slate-300 text-xs whitespace-nowrap">
          {ts}
        </td>
        <td className="px-4 py-2">
          <LevelBadge level={error.level} />
        </td>
        <td className="px-4 py-2 text-white font-mono text-xs">
          {error.error_type}
        </td>
        <td className="px-4 py-2 text-slate-300 text-xs max-w-xs truncate">
          {truncatedMsg}
        </td>
        <td className="px-4 py-2 text-slate-400 text-xs">
          {error.module || "--"}
        </td>
      </tr>
      {isExpanded && (
        <tr data-testid={`error-detail-row-${error.id}`}>
          <td colSpan={5} className="p-0">
            <ErrorDetailView errorId={error.id} />
          </td>
        </tr>
      )}
    </>
  );
}

export function AdminErrorsSection({ isOpen }: { isOpen: boolean }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (isOpen && !loaded) {
      setLoaded(true);
    }
  }, [isOpen, loaded]);

  if (!loaded) return null;

  return <ErrorsContent />;
}
