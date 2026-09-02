import { useTranslation } from "react-i18next";

export interface ScanSummary {
  cardsTotal: number;
  cardsProcessed: number;
  cardsFailed: number;
  observationsSaved: number;
  notFoundCount: number;
  rateLimitedCount: number;
  durationMs: number;
}

interface ScanSummaryCardProps {
  summary: ScanSummary;
  onDismiss: () => void;
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

export function ScanSummaryCard({ summary, onDismiss }: ScanSummaryCardProps) {
  const { t } = useTranslation();

  const hasFailed = summary.cardsFailed > 0;
  const otherErrors =
    summary.cardsFailed - summary.notFoundCount - summary.rateLimitedCount;

  return (
    <div
      className="bg-slate-800 border border-slate-600 rounded-lg px-4 py-4 space-y-3"
      data-testid="scan-summary-card"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {hasFailed ? (
            <svg
              className="h-5 w-5 text-amber-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              data-testid="scan-summary-warning-icon"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          ) : (
            <svg
              className="h-5 w-5 text-emerald-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              data-testid="scan-summary-success-icon"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
          )}
          <span className="text-sm font-medium text-white">
            {hasFailed
              ? t("scan.summary.titleWarning")
              : t("scan.summary.title")}
          </span>
        </div>
        <button
          onClick={onDismiss}
          className="text-slate-400 hover:text-white transition-colors"
          title={t("scan.summary.dismiss")}
          data-testid="scan-summary-dismiss"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Stat grid */}
      <div className="flex flex-wrap gap-4 text-sm">
        {/* Priced -- always shown */}
        <div data-testid="scan-summary-priced">
          <span className="text-emerald-400 font-bold">
            {summary.observationsSaved}
          </span>
          <span className="text-slate-400 ml-1">
            / {summary.cardsTotal} {t("scan.summary.priced")}
          </span>
        </div>

        {/* Not Found -- only if > 0 */}
        {summary.notFoundCount > 0 && (
          <div data-testid="scan-summary-not-found">
            <span className="text-amber-400 font-bold">
              {summary.notFoundCount}
            </span>
            <span className="text-slate-400 ml-1">
              {t("scan.summary.notFound")}
            </span>
          </div>
        )}

        {/* Rate Limited -- only if > 0 */}
        {summary.rateLimitedCount > 0 && (
          <div data-testid="scan-summary-rate-limited">
            <span className="text-red-400 font-bold">
              {summary.rateLimitedCount}
            </span>
            <span className="text-slate-400 ml-1">
              {t("scan.summary.rateLimited")}
            </span>
          </div>
        )}

        {/* Other Errors -- only if > 0 */}
        {otherErrors > 0 && (
          <div data-testid="scan-summary-other-errors">
            <span className="text-slate-300 font-bold">{otherErrors}</span>
            <span className="text-slate-400 ml-1">
              {t("scan.summary.otherErrors")}
            </span>
          </div>
        )}
      </div>

      {/* Footer -- duration */}
      <div className="text-xs text-slate-500" data-testid="scan-summary-duration">
        {t("scan.summary.duration", { time: formatDuration(summary.durationMs) })}
      </div>
    </div>
  );
}
