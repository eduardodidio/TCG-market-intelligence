import type { ScanRun } from "../types/api";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700";
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
  if (scans.length === 0) {
    return (
      <div
        className="rounded-lg border border-slate-700 bg-slate-800 p-8 text-center text-slate-400"
        data-testid="scans-empty"
      >
        No scan runs yet.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700" data-testid="scans-table">
      <table className="w-full text-sm text-left">
        <thead className="bg-slate-800 text-xs uppercase text-slate-400 border-b border-slate-700">
          <tr>
            <th className="px-4 py-3">ID</th>
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Cards</th>
            <th className="px-4 py-3">Processed</th>
            <th className="px-4 py-3">Failed</th>
            <th className="px-4 py-3">Obs</th>
            <th className="px-4 py-3">Started</th>
            <th className="px-4 py-3">Duration</th>
          </tr>
        </thead>
        <tbody>
          {scans.map((scan) => (
            <tr
              key={scan.id}
              className={`border-b border-slate-700 bg-slate-800/50 hover:bg-slate-700/50 transition-colors ${
                onSelect ? "cursor-pointer" : ""
              }`}
              onClick={() => onSelect?.(scan.id)}
              data-testid={`scan-row-${scan.id}`}
            >
              <td className="px-4 py-3 font-mono text-slate-300">{scan.id}</td>
              <td className="px-4 py-3 text-slate-300">{scan.scan_type}</td>
              <td className="px-4 py-3">
                <StatusBadge status={scan.status} />
              </td>
              <td className="px-4 py-3 text-slate-300">{scan.cards_total}</td>
              <td className="px-4 py-3 text-slate-300">{scan.cards_processed}</td>
              <td className="px-4 py-3 text-slate-300">{scan.cards_failed}</td>
              <td className="px-4 py-3 text-slate-300">{scan.observations_saved}</td>
              <td className="px-4 py-3 text-slate-300">{formatDateTime(scan.started_at)}</td>
              <td className="px-4 py-3 text-slate-300">
                {formatDuration(scan.started_at, scan.finished_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
