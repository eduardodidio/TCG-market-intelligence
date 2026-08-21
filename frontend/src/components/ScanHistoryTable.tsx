import { useTranslation } from "react-i18next";
import type { ScanRun } from "../types/api";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-tcg-muted/20 text-tcg-muted",
  running: "bg-tcg-info/20 text-tcg-info",
  completed: "bg-tcg-gain/20 text-tcg-gain",
  failed: "bg-tcg-loss/20 text-tcg-loss",
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-tcg-muted/20 text-tcg-muted";
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${style}`}
      data-testid={`status-badge-${status}`}
    >
      {status}
    </span>
  );
}

function formatDuration(started: string | null, finished: string | null): string {
  if (!started) return "--";
  if (!finished) return "running...";
  const ms = new Date(finished).getTime() - new Date(started).getTime();
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "--";
  const d = new Date(iso);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  return `${day}/${month} ${hours}:${mins}`;
}

interface ScanHistoryTableProps {
  scans: ScanRun[];
  onSelect?: (id: number) => void;
}

export function ScanHistoryTable({ scans, onSelect }: ScanHistoryTableProps) {
  const { t } = useTranslation();

  if (scans.length === 0) {
    return (
      <div
        className="rounded-tcg-md border border-tcg-border bg-tcg-card p-8 text-center text-tcg-muted"
        data-testid="scans-empty"
      >
        {t("scans.noScans")}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-tcg-md border border-tcg-border" data-testid="scans-table">
      <table className="w-full text-sm text-left">
        <thead className="bg-tcg-card-alt text-xs uppercase text-tcg-muted border-b border-tcg-border">
          <tr>
            <th className="px-4 py-3">{t("scans.columnId")}</th>
            <th className="px-4 py-3">{t("scans.columnType")}</th>
            <th className="px-4 py-3">{t("scans.columnStatus")}</th>
            <th className="px-4 py-3">{t("scans.columnCards")}</th>
            <th className="px-4 py-3">{t("scans.columnProcessed")}</th>
            <th className="px-4 py-3">{t("scans.columnFailed")}</th>
            <th className="px-4 py-3">{t("scans.columnObs")}</th>
            <th className="px-4 py-3">{t("scans.columnStarted")}</th>
            <th className="px-4 py-3">{t("scans.columnDuration")}</th>
          </tr>
        </thead>
        <tbody>
          {scans.map((scan) => (
            <tr
              key={scan.id}
              className={`border-b border-tcg-border/50 bg-tcg-card/50 hover:bg-tcg-card-alt transition-colors ${
                onSelect ? "cursor-pointer" : ""
              }`}
              onClick={() => onSelect?.(scan.id)}
              data-testid={`scan-row-${scan.id}`}
            >
              <td className="px-4 py-3 font-mono text-tcg-muted">{scan.id}</td>
              <td className="px-4 py-3 text-tcg-muted">{scan.scan_type}</td>
              <td className="px-4 py-3">
                <StatusBadge status={scan.status} />
              </td>
              <td className="px-4 py-3 text-tcg-muted">{scan.cards_total}</td>
              <td className="px-4 py-3 text-tcg-muted">{scan.cards_processed}</td>
              <td className="px-4 py-3 text-tcg-muted">{scan.cards_failed}</td>
              <td className="px-4 py-3 text-tcg-muted">{scan.observations_saved}</td>
              <td className="px-4 py-3 text-tcg-muted">{formatDateTime(scan.started_at)}</td>
              <td className="px-4 py-3 text-tcg-muted">
                {formatDuration(scan.started_at, scan.finished_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
