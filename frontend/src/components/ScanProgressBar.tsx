import { useTranslation } from "react-i18next";

interface ScanProgressBarProps {
  processed: number;
  total: number;
  currentCardName?: string;
  priceFoundCount: number;
  startTime: number;
  isRefreshing: boolean;
  isDone: boolean;
  error: string | null;
  onCancel?: () => void;
}

function formatEta(ms: number): string {
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `< 1m`;
  return `${minutes}m ${seconds}s`;
}

export function ScanProgressBar({
  processed,
  total,
  currentCardName,
  priceFoundCount,
  startTime,
  isRefreshing,
  isDone,
  error,
  onCancel,
}: ScanProgressBarProps) {
  const { t } = useTranslation();
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0;

  // Calculate ETA
  const elapsed = Date.now() - startTime;
  const avgPerCard = processed > 0 ? elapsed / processed : 0;
  const remaining = (total - processed) * avgPerCard;
  const showEta = processed >= 3 && isRefreshing;

  if (error) {
    return (
      <div
        className="bg-red-900/30 border border-red-500/40 rounded-lg px-4 py-3 text-sm"
        data-testid="scan-progress-error"
      >
        <span className="text-red-400">{t("scan.streaming.failed", { error })}</span>
      </div>
    );
  }

  if (isDone) {
    return (
      <div
        className="bg-emerald-900/30 border border-emerald-500/40 rounded-lg px-4 py-3 text-sm flex items-center gap-2"
        data-testid="scan-progress-done"
      >
        <svg className="h-4 w-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        <span className="text-emerald-400">
          {t("scan.streaming.complete", { total, prices: priceFoundCount })}
        </span>
      </div>
    );
  }

  if (!isRefreshing) return null;

  return (
    <div
      className="bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 space-y-2"
      data-testid="scan-progress-bar"
    >
      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-cyan-400 rounded-full transition-all duration-300"
            style={{ width: `${pct}%` }}
            data-testid="scan-progress-fill"
          />
        </div>
        <span className="text-xs text-slate-300 whitespace-nowrap font-mono" data-testid="scan-progress-text">
          {processed}/{total} ({pct}%)
        </span>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-slate-400 hover:text-red-400 transition-colors"
            title={t("common.cancel")}
            data-testid="scan-cancel-btn"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Details row */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <div className="truncate max-w-[50%]">
          {currentCardName ? (
            <span data-testid="scan-current-card">
              {t("scan.streaming.scanning", { cardName: currentCardName })}
            </span>
          ) : (
            <span>{t("scan.streaming.connecting")}</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {processed > 0 && (
            <span data-testid="scan-prices-found">
              {t("scan.streaming.pricesFound", { found: priceFoundCount, total: processed })}
            </span>
          )}
          {showEta && (
            <span data-testid="scan-eta">
              {t("scan.streaming.eta", { time: formatEta(remaining) })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
