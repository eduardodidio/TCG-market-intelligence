import { useTranslation } from "react-i18next";

const STATUS_STYLES: Record<string, string> = {
  legal: "bg-green-900/30 text-green-400 border-green-700",
  banned: "bg-red-900/30 text-red-400 border-red-700",
  restricted: "bg-yellow-900/30 text-yellow-400 border-yellow-700",
  not_legal: "bg-slate-700/50 text-slate-400 border-slate-600",
};

const STATUS_I18N_KEYS: Record<string, string> = {
  legal: "banlist.legal",
  banned: "banlist.banned",
  restricted: "banlist.restricted",
  not_legal: "banlist.not_legal",
};

interface LegalityBadgeProps {
  status: string;
  format?: string;
  size?: "sm" | "md";
}

export function LegalityBadge({
  status,
  format,
  size = "md",
}: LegalityBadgeProps) {
  const { t } = useTranslation();

  const style = STATUS_STYLES[status] || STATUS_STYLES.not_legal;
  const statusText = t(STATUS_I18N_KEYS[status] || "banlist.not_legal");
  const formatLabel = format
    ? format.charAt(0).toUpperCase() + format.slice(1)
    : null;

  const sizeClasses =
    size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border font-medium ${style} ${sizeClasses}`}
      data-testid={`legality-badge-${status}`}
    >
      {formatLabel && (
        <span className="font-semibold" data-testid="legality-format">
          {formatLabel}
        </span>
      )}
      <span data-testid="legality-status">{statusText}</span>
    </span>
  );
}
