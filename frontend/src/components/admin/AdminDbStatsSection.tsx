import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchDbStats } from "../../api/admin";
import type { DbStatsResponse } from "../../api/admin";

function DbStatsContent() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<DbStatsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    const resp = await fetchDbStats();
    if (resp.errors.length > 0) {
      setError(resp.errors.map((e) => e.message).join("; "));
      setStats(null);
    } else {
      setStats(resp.data);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 60_000);
    return () => clearInterval(interval);
  }, [loadStats]);

  if (loading && !stats) {
    return (
      <p className="text-slate-400" data-testid="db-stats-loading">
        {t("common.loading")}
      </p>
    );
  }

  if (error) {
    return (
      <p className="text-red-400" data-testid="db-stats-error">
        {error}
      </p>
    );
  }

  if (!stats) return null;

  return (
    <div data-testid="db-stats-section" className="space-y-6">
      {/* Table sizes */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <h3 className="px-4 py-3 text-white font-medium border-b border-slate-700">
          {t("admin.dbStats.tableSizes")}
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left" data-testid="db-stats-tables">
            <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
              <tr>
                <th className="px-4 py-2">{t("admin.dbStats.table")}</th>
                <th className="px-4 py-2 text-right">{t("admin.dbStats.rows")}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.tables)
                .sort(([, a], [, b]) => b - a)
                .map(([table, count]) => (
                  <tr key={table} className="border-t border-slate-700">
                    <td className="px-4 py-2 text-slate-300 font-mono text-xs">
                      {table}
                    </td>
                    <td className="px-4 py-2 text-white text-right font-mono">
                      {count.toLocaleString()}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Last sync dates */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <h3 className="px-4 py-3 text-white font-medium border-b border-slate-700">
          {t("admin.dbStats.lastSync")}
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left" data-testid="db-stats-sync">
            <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
              <tr>
                <th className="px-4 py-2">{t("admin.dbStats.source")}</th>
                <th className="px-4 py-2">{t("admin.dbStats.lastSyncDate")}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.last_sync).map(([source, date]) => (
                <tr key={source} className="border-t border-slate-700">
                  <td className="px-4 py-2 text-slate-300 capitalize">{source}</td>
                  <td className="px-4 py-2 text-white text-xs">
                    {date ? new Date(date).toLocaleString() : "--"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Connection info */}
      {stats.connection_info && Object.keys(stats.connection_info).length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="text-white font-medium mb-3">
            {t("admin.dbStats.connectionInfo")}
          </h3>
          <div className="space-y-1">
            {Object.entries(stats.connection_info).map(([key, val]) => (
              <div key={key} className="flex gap-2 text-sm">
                <span className="text-slate-400">{key}:</span>
                <span className="text-white font-mono text-xs">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function AdminDbStatsSection({ isOpen }: { isOpen: boolean }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (isOpen && !loaded) {
      setLoaded(true);
    }
  }, [isOpen, loaded]);

  if (!loaded) return null;

  return <DbStatsContent />;
}
