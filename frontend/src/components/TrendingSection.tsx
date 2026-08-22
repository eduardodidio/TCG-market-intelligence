import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { fetchTrending } from "../api/trending";
import { TrendingCard } from "./TrendingCard";
import { ErrorBanner } from "./ErrorBanner";
import { EmptyState } from "./EmptyState";
import type { TrendingResponse } from "../types/api";

interface TrendingSectionProps {
  direction: "gainers" | "losers";
  period: string;
  currency: string;
  limit?: number;
}

function SkeletonCard() {
  return (
    <div className="flex-shrink-0 w-44 rounded-lg bg-slate-800 border border-slate-700 p-3 animate-pulse" data-testid="skeleton-card">
      <div className="w-16 h-[90px] mx-auto mb-2 rounded bg-slate-700" />
      <div className="h-4 bg-slate-700 rounded w-3/4 mb-1" />
      <div className="h-3 bg-slate-700 rounded w-1/2 mb-1" />
      <div className="h-4 bg-slate-700 rounded w-2/3 mt-1" />
      <div className="h-1.5 bg-slate-700 rounded-full mt-2" />
    </div>
  );
}

export function TrendingSection({ direction, period, currency, limit }: TrendingSectionProps) {
  const { t } = useTranslation();

  const params: Record<string, string> = { period, currency };
  if (limit) params.limit = String(limit);

  const { data, loading, error, refetch } = useApi<TrendingResponse>(
    (signal) => fetchTrending(direction, params),
    [direction, period, currency, limit],
  );

  const titleKey = direction === "gainers" ? "trending.trendingUp" : "trending.trendingDown";
  const icon = direction === "gainers" ? "\u2191" : "\u2193";
  const iconColor = direction === "gainers" ? "text-green-400" : "text-red-400";

  return (
    <section data-testid={`trending-section-${direction}`}>
      {/* Section header */}
      <div className="flex items-center gap-2 mb-3">
        <span className={`text-lg font-bold ${iconColor}`}>{icon}</span>
        <h2 className="text-lg font-semibold text-white">{t(titleKey)}</h2>
        {data?.cached && (
          <span className="text-xs text-slate-500 ml-auto" data-testid="cached-badge">
            {t("trending.cached", { time: _relativeTime(data.computed_at) })}
          </span>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex gap-3 overflow-x-auto pb-2" data-testid="trending-loading">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <ErrorBanner message={error} variant="full" onRetry={refetch} />
      )}

      {/* Empty state */}
      {!loading && !error && data && data.cards.length === 0 && (
        <EmptyState message={t("trending.noTrending")} />
      )}

      {/* Cards scroll container */}
      {!loading && !error && data && data.cards.length > 0 && (
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
          {data.cards.map((entry) => (
            <TrendingCard key={entry.card_id} entry={entry} />
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * Compute relative time string from ISO date.
 */
function _relativeTime(isoDate: string): string {
  try {
    const diff = Date.now() - new Date(isoDate).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return "<1 min";
    if (minutes < 60) return `${minutes} min`;
    return `${Math.floor(minutes / 60)}h`;
  } catch {
    return "?";
  }
}
