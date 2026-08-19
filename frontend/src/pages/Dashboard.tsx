import { useEffect } from "react";
import { useApi } from "../hooks/useApi";
import { fetchMarketStats, fetchMovers } from "../api/market";
import { formatBRL, formatDate } from "../utils/format";
import { KpiCard } from "../components/KpiCard";
import { MoversPreview } from "../components/MoversPreview";
import { ErrorBanner } from "../components/ErrorBanner";
import { SkeletonKpi, SkeletonTable } from "../components/Skeleton";
import type { MarketStats, MoversResponse } from "../types/api";

export function Dashboard() {
  useEffect(() => {
    document.title = "Dashboard | TCG Market";
  }, []);

  const stats = useApi<MarketStats>(() => fetchMarketStats());
  const movers = useApi<MoversResponse>(() =>
    fetchMovers({ period: "7d", limit: "5" }),
  );

  const loading = stats.loading || movers.loading;
  const error = stats.error || movers.error;

  if (loading) {
    return (
      <div data-testid="page-dashboard">
        <h1 className="mb-6 text-2xl font-bold text-white">Market Overview</h1>
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonKpi key={i} />
          ))}
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <SkeletonTable rows={5} />
          <SkeletonTable rows={5} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="page-dashboard">
        <h1 className="mb-6 text-2xl font-bold text-white">Market Overview</h1>
        <ErrorBanner
          message={error}
          variant="full"
          onRetry={() => {
            stats.refetch();
            movers.refetch();
          }}
        />
      </div>
    );
  }

  const marketStats = stats.data;
  const moversData = movers.data;

  const dateRange =
    marketStats?.date_range_start && marketStats?.date_range_end
      ? `${formatDate(marketStats.date_range_start)} - ${formatDate(marketStats.date_range_end)}`
      : "--";

  return (
    <div data-testid="page-dashboard">
      <h1 className="mb-6 text-2xl font-bold text-white">Market Overview</h1>

      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          title="Total Cards"
          value={String(marketStats?.total_cards ?? 0)}
          subtitle="cards tracked"
        />
        <KpiCard
          title="Total Observations"
          value={String(marketStats?.total_observations ?? 0)}
          subtitle="price points"
        />
        <KpiCard
          title="Average Price"
          value={formatBRL(marketStats?.avg_price ?? null)}
          subtitle="across all cards"
        />
        <KpiCard
          title="Data Range"
          value={dateRange}
          subtitle="collection period"
        />
      </div>

      {moversData && (
        <MoversPreview
          gainers={moversData.gainers}
          losers={moversData.losers}
        />
      )}
    </div>
  );
}
