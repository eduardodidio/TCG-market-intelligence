import { useTranslation } from "react-i18next";
import { LegalityBadge } from "./LegalityBadge";

interface StatusTransitionProps {
  oldStatus: string | null;
  newStatus: string;
  size?: "sm" | "md";
}

function arrowColor(newStatus: string): string {
  if (newStatus === "banned" || newStatus === "restricted") {
    return "text-red-400";
  }
  if (newStatus === "legal") {
    return "text-green-400";
  }
  return "text-slate-400";
}

export function StatusTransition({
  oldStatus,
  newStatus,
  size = "sm",
}: StatusTransitionProps) {
  const { t } = useTranslation();

  if (oldStatus === null) {
    return (
      <div className="flex items-center gap-1.5" data-testid="status-transition">
        <span className="text-xs text-slate-500" data-testid="initial-label">
          {t("banHistory.transition.initial")}
        </span>
        <LegalityBadge status={newStatus} size={size} />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5" data-testid="status-transition">
      <LegalityBadge status={oldStatus} size={size} />
      <svg
        className={`h-4 w-4 flex-shrink-0 ${arrowColor(newStatus)}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
        data-testid="transition-arrow"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 7l5 5m0 0l-5 5m5-5H6"
        />
      </svg>
      <LegalityBadge status={newStatus} size={size} />
    </div>
  );
}
