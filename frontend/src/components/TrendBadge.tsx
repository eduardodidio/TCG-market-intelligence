import { useTranslation } from "react-i18next";

interface TrendBadgeProps {
  changePct: number | null;
  size?: "sm" | "md";
}

/**
 * Arrow icon (up/down/dash) + percentage change indicator.
 * Green for positive, red for negative, gray for zero/flat.
 * Renders nothing when changePct is null (no data).
 */
export function TrendBadge({ changePct, size = "sm" }: TrendBadgeProps) {
  const { t } = useTranslation();

  if (changePct === null || changePct === undefined) {
    return null;
  }

  const textSize = size === "sm" ? "text-xs" : "text-sm";
  const iconSize = size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5";

  let colorClass: string;
  let arrowPath: string;
  let ariaLabel: string;

  if (changePct > 0) {
    colorClass = "text-green-400";
    arrowPath = "M5 15l7-7 7 7"; // up arrow
    ariaLabel = t("trend.up", { defaultValue: "Trending up" });
  } else if (changePct < 0) {
    colorClass = "text-red-400";
    arrowPath = "M19 9l-7 7-7-7"; // down arrow
    ariaLabel = t("trend.down", { defaultValue: "Trending down" });
  } else {
    colorClass = "text-slate-400";
    arrowPath = "M5 12h14"; // dash
    ariaLabel = t("trend.flat", { defaultValue: "No change" });
  }

  const formatted = changePct > 0
    ? `+${changePct.toFixed(1)}%`
    : `${changePct.toFixed(1)}%`;

  return (
    <span
      className={`inline-flex items-center gap-0.5 ${colorClass} ${textSize}`}
      data-testid="trend-badge"
      aria-label={`${ariaLabel}: ${formatted}`}
    >
      <svg
        className={iconSize}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2.5}
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={arrowPath} />
      </svg>
      <span>{formatted}</span>
    </span>
  );
}
