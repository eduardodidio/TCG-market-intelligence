interface FreshnessIndicatorProps {
  lastCollectionAt: string | null;
  status: string;
}

function formatRelativeTime(isoDate: string): string {
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const diffMs = now - then;

  if (diffMs < 0 || Number.isNaN(diffMs)) {
    return "just now";
  }

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;

  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

const STATUS_DOT_CLASSES: Record<string, string> = {
  healthy: "bg-green-400",
  stale: "bg-yellow-400",
  error: "bg-red-400",
};

export function FreshnessIndicator({
  lastCollectionAt,
  status,
}: FreshnessIndicatorProps) {
  const dotClass = STATUS_DOT_CLASSES[status] ?? "bg-slate-400";

  const label =
    lastCollectionAt !== null
      ? `Last updated: ${formatRelativeTime(lastCollectionAt)}`
      : "Data freshness: Unknown";

  return (
    <span
      data-testid="freshness-indicator"
      className="inline-flex items-center gap-1.5 rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300"
    >
      <span
        data-testid="freshness-dot"
        className={`inline-block h-2 w-2 rounded-full ${dotClass}`}
      />
      {label}
    </span>
  );
}
