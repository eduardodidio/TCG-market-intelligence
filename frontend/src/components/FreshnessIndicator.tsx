import { useTranslation } from "react-i18next";

interface FreshnessIndicatorProps {
  lastCollectionAt: string | null;
  status: string;
}

function useRelativeTime() {
  const { t } = useTranslation();

  return function formatRelativeTime(isoDate: string): string {
    const now = Date.now();
    const then = new Date(isoDate).getTime();
    const diffMs = now - then;

    if (diffMs < 0 || Number.isNaN(diffMs)) {
      return t("freshness.justNow");
    }

    const seconds = Math.floor(diffMs / 1000);
    if (seconds < 60) return t("freshness.justNow");

    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return t("freshness.minutesAgo", { count: minutes });

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return t("freshness.hoursAgo", { count: hours });

    const days = Math.floor(hours / 24);
    return t("freshness.daysAgo", { count: days });
  };
}

const STATUS_DOT_CLASSES: Record<string, string> = {
  healthy: "bg-tcg-gain",
  stale: "bg-tcg-warning",
  error: "bg-tcg-loss",
};

export function FreshnessIndicator({
  lastCollectionAt,
  status,
}: FreshnessIndicatorProps) {
  const { t } = useTranslation();
  const formatRelativeTime = useRelativeTime();
  const dotClass = STATUS_DOT_CLASSES[status] ?? "bg-tcg-muted";

  const label =
    lastCollectionAt !== null
      ? t("freshness.lastUpdated", { time: formatRelativeTime(lastCollectionAt) })
      : t("freshness.unknown");

  return (
    <span
      data-testid="freshness-indicator"
      className="inline-flex items-center gap-1.5 rounded-full bg-tcg-card border border-tcg-border px-3 py-1 text-xs text-tcg-muted"
    >
      <span
        data-testid="freshness-dot"
        className={`inline-block h-2 w-2 rounded-full ${dotClass}`}
      />
      {label}
    </span>
  );
}
