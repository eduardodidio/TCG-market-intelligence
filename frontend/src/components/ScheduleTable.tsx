import { useTranslation } from "react-i18next";
import type { ScheduleResponse } from "../types/api";

interface ScheduleTableProps {
  schedules: ScheduleResponse[];
  onPauseResume: (id: number, newStatus: "active" | "paused") => void;
  onTrigger: (id: number) => void;
  onEdit: (schedule: ScheduleResponse) => void;
  onDelete: (id: number) => void;
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const colorMap: Record<string, string> = {
    active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    paused: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    disabled: "bg-red-500/20 text-red-400 border-red-500/30",
  };
  const colors = colorMap[status] || colorMap.disabled;
  const labelKey = `schedules.${status}` as const;

  return (
    <span
      className={`inline-flex px-2 py-0.5 text-xs font-medium rounded border ${colors}`}
      data-testid={`status-badge-${status}`}
    >
      {t(labelKey)}
    </span>
  );
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatFutureTime(dateStr: string | null): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  const now = new Date();
  const diff = d.getTime() - now.getTime();
  if (diff < 0) return formatRelativeTime(dateStr);
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `in ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `in ${hours}h`;
  const days = Math.floor(hours / 24);
  return `in ${days}d`;
}

export function ScheduleTable({
  schedules,
  onPauseResume,
  onTrigger,
  onEdit,
  onDelete,
}: ScheduleTableProps) {
  const { t } = useTranslation();

  return (
    <div className="overflow-x-auto" data-testid="schedule-table">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-slate-400 uppercase border-b border-slate-600">
          <tr>
            <th className="px-4 py-3">{t("schedules.name")}</th>
            <th className="px-4 py-3">{t("schedules.cron")}</th>
            <th className="px-4 py-3">{t("schedules.status")}</th>
            <th className="px-4 py-3">{t("schedules.lastRun")}</th>
            <th className="px-4 py-3">{t("schedules.nextRun")}</th>
            <th className="px-4 py-3">{t("schedules.errors")}</th>
            <th className="px-4 py-3">{t("schedules.actions")}</th>
          </tr>
        </thead>
        <tbody>
          {schedules.map((schedule) => (
            <tr
              key={schedule.id}
              className="border-b border-slate-700 hover:bg-slate-800/50"
              data-testid={`schedule-row-${schedule.id}`}
            >
              <td className="px-4 py-3 font-medium text-white">
                {schedule.name}
                {schedule.description && (
                  <span className="block text-xs text-slate-400 mt-0.5">
                    {schedule.description}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 font-mono text-slate-300">
                {schedule.cron_expression}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={schedule.status} />
                {schedule.status === "paused" && schedule.error_count > 0 && (
                  <span className="block text-xs text-amber-400/70 mt-0.5" data-testid={`pause-reason-${schedule.id}`}>
                    {t("schedules.pausedByErrors", { count: schedule.error_count })}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-slate-300">
                {formatRelativeTime(schedule.last_run_at)}
              </td>
              <td className="px-4 py-3 text-slate-300">
                {formatFutureTime(schedule.next_run_at)}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`font-mono ${
                    schedule.error_count >= schedule.max_retries
                      ? "text-red-400"
                      : "text-slate-300"
                  }`}
                >
                  {schedule.error_count}/{schedule.max_retries}
                </span>
              </td>
              <td className="px-4 py-3">
                <div className="flex gap-1">
                  {/* Pause/Resume */}
                  <button
                    onClick={() =>
                      onPauseResume(
                        schedule.id,
                        schedule.status === "active" ? "paused" : "active",
                      )
                    }
                    className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                    title={
                      schedule.status === "active"
                        ? t("schedules.pause")
                        : t("schedules.resume")
                    }
                    data-testid={`action-pause-${schedule.id}`}
                  >
                    {schedule.status === "active" ? (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    )}
                  </button>

                  {/* Trigger Now */}
                  <button
                    onClick={() => onTrigger(schedule.id)}
                    className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-cyan-400 transition-colors"
                    title={t("schedules.trigger")}
                    data-testid={`action-trigger-${schedule.id}`}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </button>

                  {/* Edit */}
                  <button
                    onClick={() => onEdit(schedule)}
                    className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                    title={t("schedules.edit")}
                    data-testid={`action-edit-${schedule.id}`}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>

                  {/* Delete */}
                  <button
                    onClick={() => onDelete(schedule.id)}
                    className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-red-400 transition-colors"
                    title={t("schedules.delete")}
                    data-testid={`action-delete-${schedule.id}`}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
