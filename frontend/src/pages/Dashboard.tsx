import { useEffect } from "react";
import { useApi } from "../hooks/useApi";
import { fetchMarketStats, fetchMovers } from "../api/market";
import { fetchCollectionHealth } from "../api/collect";
import { fetchCollectionSummary } from "../api/collection";
import { formatBRL, formatDate } from "../utils/format";
import { KpiCard } from "../components/KpiCard";
import { MoversPreview } from "../components/MoversPreview";
import { EmptyState } from "../components/EmptyState";
import { FreshnessIndicator } from "../components/FreshnessIndicator";
import { ErrorBanner } from "../components/ErrorBanner";
import { SkeletonKpi, SkeletonTable } from "../components/Skeleton";
import type {
  CollectionHealth,
  CollectionSummary,
  MarketStats,
  MoversResponse,
} from "../types/api";

export function Dashboard() {
  useEffect(() => {
    document.title = "Dashboard | TCG Market";
  }, []);

  const stats = useApi<MarketStats>(() => fetchMarketStats());
  const movers = useApi<MoversResponse>(() =>
    fetchMovers({ period: "30d", limit: "5" }),
  );
  const health = useApi<CollectionHealth>(() => fetchCollectionHealth());
  const collectionSummary = useApi<CollectionSummary>(() =>
    fetchCollectionSummary(),
  );

  const loading = stats.loading || movers.loading;
  const error = stats.error || movers.error;

  // Collection summary is independent — never blocks dashboard rendering
  const summaryData = collectionSummary.data;
  const coverage =
    summaryData && summaryData.total_unique > 0
      ? Math.round((summaryData.linked_count / summaryData.total_unique) * 100)
      : 0;

  // Freshness indicator is independent — never blocks dashboard rendering
  const freshnessIndicator = !health.loading && !health.error && health.data ? (
    <FreshnessIndicator
      lastCollectionAt={health.data.last_collection_at}
      status={health.data.status}
    />
  ) : null;

  if (loading) {
    return (
      <div data-testid="page-dashboard">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-white">My Collection</h1>
          {freshnessIndicator}
        </div>
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonKpi key={i} />
          ))}
        </div>
        <h2 className="mb-4 text-xl font-semibold text-white">Market Overview</h2>
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
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-white">My Collection</h1>
          {freshnessIndicator}
        </div>
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

  const hasMarketData = (marketStats?.total_cards ?? 0) > 0;
  const hasMoversData =
    moversData &&
    (moversData.gainers.length > 0 || moversData.losers.length > 0);

  return (
    <div data-testid="page-dashboard">
      {/* Collection hero section */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-white">My Collection</h1>
        {freshnessIndicator}
      </div>

      {/* Collection KPIs */}
      {!collectionSummary.loading && !collectionSummary.error && summaryData ? (
        <div
          className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4"
          data-testid="collection-kpis"
        >
          <KpiCard
            title="Collection Cards"
            value={String(summaryData.total_unique)}
            subtitle="unique cards"
          />
          <KpiCard
            title="Total Copies"
            value={String(summaryData.total_cards)}
            subtitle="total quantity"
          />
          <KpiCard
            title="Est. Collection Value"
            value={formatBRL(summaryData.total_value)}
            subtitle="based on latest prices"
          />
          <KpiCard
            title="Coverage"
            value={`${coverage}%`}
            subtitle="cards with price data"
          />
        </div>
      ) : !collectionSummary.loading ? (
        <div className="mb-8" data-testid="collection-empty">
          <EmptyState message="Import your collection and sync with MYP to see your stats here." />
        </div>
      ) : null}

      {/* Market Overview section */}
      <h2 className="mb-4 text-xl font-semibold text-white">Market Overview</h2>

      {hasMarketData ? (
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4" data-testid="market-kpis">
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
      ) : (
        <div className="mb-8" data-testid="market-empty">
          <EmptyState message="Import your collection and sync with MYP to see market data here." />
        </div>
      )}

      {hasMoversData ? (
        <MoversPreview
          gainers={moversData.gainers}
          losers={moversData.losers}
        />
      ) : (
        !hasMarketData && (
          <div data-testid="movers-empty">
            <EmptyState message="Not enough price history for movers. Run a sync and check back." />
          </div>
        )
      )}
    </div>
  );
}
