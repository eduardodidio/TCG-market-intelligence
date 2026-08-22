import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { fetchVolatile } from "../api/market";
import { TrendingCard } from "./TrendingCard";
import { EmptyState } from "./EmptyState";
import type { TrendingResponse } from "../types/api";

interface VolatileSectionProps {
  period: string;
  currency: string;
}

function SkeletonCard() {
  return (
    <div className="flex-shrink-0 w-44 rounded-lg bg-slate-800 border border-slate-700 p-3 animate-pulse">
      <div className="w-16 h-[90px] mx-auto mb-2 rounded bg-slate-700" />
      <div className="h-4 bg-slate-700 rounded w-3/4 mb-1" />
      <div className="h-3 bg-slate-700 rounded w-1/2 mb-1" />
      <div className="h-4 bg-slate-700 rounded w-2/3 mt-1" />
    </div>
  );
}

export function VolatileSection({ period, currency }: VolatileSectionProps) {
  const { t } = useTranslation();

  const { data, loading, error } = useApi<TrendingResponse>(
    () => fetchVolatile({ period, currency }),
    [period, currency],
  );

  // Graceful degradation: hide entirely on error or empty
  if (error || (!loading && (!data || data.cards.length === 0))) {
    if (!loading && data && data.cards.length === 0) {
      return (
        <section data-testid="volatile-section">
          <h2 className="text-lg font-semibold text-white mb-3">
            {t("marketPage.section.mostVolatile")}
          </h2>
          <EmptyState message={t("marketPage.volatile.empty")} />
        </section>
      );
    }
    return null;
  }

  if (loading) {
    return (
      <section data-testid="volatile-section">
        <h2 className="text-lg font-semibold text-white mb-3">
          {t("marketPage.section.mostVolatile")}
        </h2>
        <div className="flex gap-3 overflow-x-auto pb-2">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </section>
    );
  }

  return (
    <section data-testid="volatile-section">
      <h2 className="text-lg font-semibold text-white mb-3">
        {t("marketPage.section.mostVolatile")}
      </h2>
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
        {data!.cards.map((entry) => (
          <TrendingCard key={entry.card_id} entry={entry} />
        ))}
      </div>
    </section>
  );
}
