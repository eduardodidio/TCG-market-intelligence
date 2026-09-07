import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchAuditLog } from "../../api/admin";
import type { AuditLogEntry } from "../../api/admin";

const LIMIT = 50;

const ACTION_TYPES = [
  "credit_adjust",
  "user_create",
  "user_delete",
  "job_trigger",
  "db_backup",
];

function AuditLogContent() {
  const { t } = useTranslation();

  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Filter state
  const [actionFilter, setActionFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);

  const loadEntries = useCallback(async () => {
    setLoading(true);
    const resp = await fetchAuditLog({
      action: actionFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      limit: LIMIT,
      offset,
    });
    if (resp.data) {
      setEntries(resp.data);
      setTotal(resp.meta.total ?? resp.data.length);
    } else {
      setEntries([]);
      setTotal(0);
    }
    setLoading(false);
  }, [actionFilter, dateFrom, dateTo, offset]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const handleFilterChange = () => {
    setOffset(0);
  };

  const hasNextPage = offset + LIMIT < total;
  const hasPrevPage = offset > 0;

  return (
    <div data-testid="audit-log-section">
      {/* Filter bar */}
      <div
        className="flex flex-wrap items-end gap-3 mb-4"
        data-testid="audit-filter-bar"
      >
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            {t("admin.audit.action")}
          </label>
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              handleFilterChange();
            }}
            className="px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
            data-testid="audit-action-filter"
          >
            <option value="">{t("admin.audit.allActions")}</option>
            {ACTION_TYPES.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">
            {t("admin.audit.dateFrom")}
          </label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              handleFilterChange();
            }}
            className="px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
            data-testid="audit-date-from"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">
            {t("admin.audit.dateTo")}
          </label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              handleFilterChange();
            }}
            className="px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
            data-testid="audit-date-to"
          />
        </div>
      </div>

      {/* Content */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        {loading ? (
          <p className="p-4 text-slate-400" data-testid="audit-loading">
            {t("common.loading")}
          </p>
        ) : entries.length === 0 ? (
          <p className="p-4 text-slate-400" data-testid="audit-empty">
            {t("admin.audit.noEntries")}
          </p>
        ) : (
          <>
            <table
              className="w-full text-sm text-left"
              data-testid="audit-table"
            >
              <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
                <tr>
                  <th className="px-4 py-2">Timestamp</th>
                  <th className="px-4 py-2">{t("admin.audit.actor")}</th>
                  <th className="px-4 py-2">{t("admin.audit.action")}</th>
                  <th className="px-4 py-2">{t("admin.audit.target")}</th>
                  <th className="px-4 py-2">{t("admin.audit.details")}</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <AuditRow
                    key={entry.id}
                    entry={entry}
                    isExpanded={expandedId === entry.id}
                    onToggle={() =>
                      setExpandedId((prev) => (prev === entry.id ? null : entry.id))
                    }
                  />
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
              <span
                className="text-xs text-slate-400"
                data-testid="audit-pagination-info"
              >
                {offset + 1}--{Math.min(offset + LIMIT, total)} {t("common.of")}{" "}
                {total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={!hasPrevPage}
                  onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                  className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                  data-testid="audit-prev"
                >
                  {t("common.prev")}
                </button>
                <button
                  disabled={!hasNextPage}
                  onClick={() => setOffset(offset + LIMIT)}
                  className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded"
                  data-testid="audit-next"
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

function AuditRow({
  entry,
  isExpanded,
  onToggle,
}: {
  entry: AuditLogEntry;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const ts = new Date(entry.timestamp).toLocaleString();
  const target = entry.target_type
    ? `${entry.target_type}:${entry.target_id || "--"}`
    : "--";
  const detailsPreview = entry.details_json
    ? entry.details_json.length > 60
      ? entry.details_json.slice(0, 60) + "..."
      : entry.details_json
    : "--";

  return (
    <>
      <tr
        className="border-t border-slate-700 hover:bg-slate-700/50 cursor-pointer"
        onClick={onToggle}
        data-testid={`audit-row-${entry.id}`}
      >
        <td className="px-4 py-2 text-slate-300 text-xs whitespace-nowrap">
          {ts}
        </td>
        <td className="px-4 py-2 text-slate-300 text-xs">
          {entry.actor_email}
        </td>
        <td className="px-4 py-2">
          <span className="text-xs bg-indigo-900 text-indigo-300 px-2 py-0.5 rounded">
            {entry.action}
          </span>
        </td>
        <td className="px-4 py-2 text-slate-400 text-xs">{target}</td>
        <td className="px-4 py-2 text-slate-400 text-xs max-w-xs truncate">
          {detailsPreview}
        </td>
      </tr>
      {isExpanded && entry.details_json && (
        <tr data-testid={`audit-detail-row-${entry.id}`}>
          <td colSpan={5} className="p-0">
            <div className="p-4 bg-slate-900 border-t border-slate-700">
              <pre
                className="text-xs text-slate-300 bg-slate-950 p-3 rounded overflow-x-auto font-mono"
                data-testid={`audit-detail-${entry.id}`}
              >
                {formatJson(entry.details_json)}
              </pre>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function formatJson(jsonStr: string): string {
  try {
    return JSON.stringify(JSON.parse(jsonStr), null, 2);
  } catch {
    return jsonStr;
  }
}

export function AdminAuditLogSection({ isOpen }: { isOpen: boolean }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (isOpen && !loaded) {
      setLoaded(true);
    }
  }, [isOpen, loaded]);

  if (!loaded) return null;

  return <AuditLogContent />;
}
