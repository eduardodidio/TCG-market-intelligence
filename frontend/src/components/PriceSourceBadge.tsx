import { useTranslation } from "react-i18next";

interface PriceSourceBadgeProps {
  priceSource?: string | null;
}

/**
 * Renders a colored badge for price sources.
 * - "jsonld_snapshot" / "myp" -> amber badge "MYP"
 * - "manual" -> blue badge "Manual"
 * Returns null for null/undefined sources.
 */
export function PriceSourceBadge({ priceSource }: PriceSourceBadgeProps) {
  const { t } = useTranslation();

  if (priceSource === "myp" || priceSource === "jsonld_snapshot") {
    return (
      <span
        data-testid="price-source-badge"
        title="MYP"
        className="inline-flex items-center gap-1 rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/30"
      >
        MYP
      </span>
    );
  }

  if (priceSource === "manual") {
    return (
      <span
        data-testid="price-source-badge"
        title={t("price.manualTooltip")}
        className="inline-flex items-center gap-1 rounded-full bg-blue-500/20 px-2.5 py-0.5 text-xs font-semibold text-blue-400 border border-blue-500/30"
      >
        <svg
          className="h-3 w-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
          />
        </svg>
        {t("price.manual")}
      </span>
    );
  }

  return null;
}
