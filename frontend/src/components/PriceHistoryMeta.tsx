import { useTranslation } from "react-i18next";
import type { PriceHistoryMeta as PriceHistoryMetaData } from "../types/api";

export interface PriceHistoryMetaProps {
  meta: PriceHistoryMetaData;
}

const SOURCE_LABEL_KEYS: Record<string, string> = {
  liga: "priceHistory.sourceLiga",
  myp: "priceHistory.sourceMyp",
  manual: "priceHistory.sourceManual",
  jsonld_snapshot: "priceHistory.sourceJsonld",
  daily_snapshot: "priceHistory.sourceSnapshot",
  daily_snapshot_backfill: "priceHistory.sourceSnapshot",
};

/** Formats an ISO date/datetime as `dd/mm` (same format as the chart axis). */
export function formatHistoryDate(dateStr: string): string {
  const [, month, day] = dateStr.slice(0, 10).split("-");
  return `${day}/${month}`;
}

export function PriceHistoryMeta({ meta }: PriceHistoryMetaProps) {
  const { t } = useTranslation();
  const isFoil = meta.variant === "foil";
  const variantText = isFoil ? t("priceHistory.variantFoil") : t("priceHistory.variantNormal");

  // Translate known sources; unknown ones are shown raw. Deduplicate labels
  // (e.g. daily_snapshot + daily_snapshot_backfill both map to "Daily snapshot").
  const sourceLabels = Array.from(
    new Set(meta.sources.map((s) => (SOURCE_LABEL_KEYS[s] ? t(SOURCE_LABEL_KEYS[s]) : s))),
  );

  return (
    <div data-testid="price-history-meta" className="flex flex-wrap items-center gap-2 mb-3 text-xs">
      <span
        data-testid="price-history-variant"
        aria-label={t("priceHistory.variantLabel", { variant: variantText })}
        className={`rounded-full px-2 py-0.5 font-medium ${
          isFoil
            ? "bg-gradient-to-r from-fuchsia-500/20 to-cyan-500/20 text-fuchsia-200"
            : "bg-slate-700 text-slate-200"
        }`}
      >
        {variantText}
      </span>

      {sourceLabels.length > 0 && (
        <span data-testid="price-history-sources" className="flex flex-wrap items-center gap-2 text-slate-400">
          <span>{t("priceHistory.sources")}:</span>
          {sourceLabels.map((label) => (
            <span key={label} className="rounded-full bg-slate-700 px-2 py-0.5 text-slate-200">
              {label}
            </span>
          ))}
        </span>
      )}

      {meta.first_observed_at && (
        <span data-testid="price-history-since" className="text-slate-400">
          {t("priceHistory.since", { date: formatHistoryDate(meta.first_observed_at) })}
        </span>
      )}

      {(meta.real_points > 0 || meta.snapshot_points > 0) && (
        <span data-testid="price-history-points" className="text-slate-400">
          {t("priceHistory.realVsSnapshot", { real: meta.real_points, snapshot: meta.snapshot_points })}
        </span>
      )}
    </div>
  );
}
