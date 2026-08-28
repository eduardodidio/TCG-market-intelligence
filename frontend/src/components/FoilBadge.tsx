import { useTranslation } from "react-i18next";

interface FoilBadgeProps {
  variant?: "compact" | "full";
}

/**
 * Visual badge indicating a foil card.
 * - "compact": small pill for card tiles (overlay)
 * - "full": larger badge for detail pages (inline)
 */
export function FoilBadge({ variant = "compact" }: FoilBadgeProps) {
  const { t } = useTranslation();

  const baseClasses =
    "inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-amber-500/20 to-yellow-500/20 font-semibold text-amber-400 border border-amber-500/30";

  const sizeClasses =
    variant === "compact"
      ? "px-2 py-0.5 text-xs"
      : "px-3 py-1 text-sm";

  return (
    <span
      data-testid="foil-badge"
      className={`${baseClasses} ${sizeClasses}`}
    >
      <svg
        className={variant === "compact" ? "h-3 w-3" : "h-4 w-4"}
        fill="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path d="M12 2l2.4 7.2H22l-6 4.8 2.4 7.2L12 16.4 5.6 21.2 8 14 2 9.2h7.6z" />
      </svg>
      {t("card.foil")}
    </span>
  );
}
