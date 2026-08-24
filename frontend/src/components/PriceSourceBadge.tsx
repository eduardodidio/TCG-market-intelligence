import { useTranslation } from "react-i18next";

interface PriceSourceBadgeProps {
  priceSource?: string | null;
}

/**
 * Renders a colored badge for notable price sources.
 * - "manual" → amber badge with pencil icon
 * - "liga" → violet badge with globe icon
 * Returns null for automatic sources (myp, jsonld_snapshot) or null/undefined.
 */
export function PriceSourceBadge({ priceSource }: PriceSourceBadgeProps) {
  const { t } = useTranslation();

  if (priceSource === "liga") {
    return (
      <span
        data-testid="price-source-badge"
        title={t("priceSource.liga")}
        className="inline-flex items-center gap-1 rounded-full bg-violet-600/20 px-2.5 py-0.5 text-xs font-semibold text-violet-400 border border-violet-500/30"
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
            d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
          />
        </svg>
        {t("priceSource.liga")}
      </span>
    );
  }

  if (priceSource !== "manual") return null;

  return (
    <span
      data-testid="price-source-badge"
      title={t("price.manualTooltip")}
      className="inline-flex items-center gap-1 rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-semibold text-amber-400 border border-amber-500/30"
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
