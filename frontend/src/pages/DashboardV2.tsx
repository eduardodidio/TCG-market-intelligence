import { useEffect } from "react";
import { useApi } from "../hooks/useApi";
import { useCurrency } from "../hooks/useCurrency";
import {
  fetchCollectionSummary,
  fetchCollectionMovers,
  fetchPortfolioSummary,
  fetchSetCompletion,
  type CollectionMoverData,
  type CollectionMoversData,
  type SetCompletionEntry,
} from "../api/collection";
import { CardImage } from "../components/CardImage";
import { formatCurrency } from "../utils/format";
import type { CollectionSummary, PortfolioSummary } from "../types/api";

function StatCard({ label, value, testId }: { label: string; value: string | number; testId?: string }) {
  return (
    <div className="v2-card p-4" data-testid={testId}>
      <p className="v2-body text-xs uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}

function MoverRow({ mover, type }: { mover: CollectionMoverData; type: "gainer" | "loser" }) {
  const sign = type === "gainer" ? "+" : "";
  const colorClass = type === "gainer" ? "text-emerald-400" : "text-red-400";

  return (
    <div className="flex items-center gap-3 py-2 border-b border-v2-border last:border-0" data-testid={`mover-${type}`}>
      <CardImage
        src={mover.image_uri}
        alt={mover.card_name}
        className="w-10 h-14 rounded overflow-hidden flex-shrink-0"
      />
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm truncate">{mover.card_name}</p>
        {mover.set_code && (
          <p className="v2-body text-xs uppercase">{mover.set_code}</p>
        )}
      </div>
      <span className={`${colorClass} text-sm font-medium`} data-testid={`mover-pct-${type}`}>
        {sign}{mover.change_pct.toFixed(1)}%
      </span>
    </div>
  );
}

function SetProgressRow({ entry }: { entry: SetCompletionEntry }) {
  const pct = entry.total > 0 ? Math.round((entry.owned / entry.total) * 100) : 0;

  return (
    <div className="py-2 border-b border-v2-border last:border-0" data-testid="set-progress">
      <div className="flex items-center justify-between mb-1">
        <span className="text-white text-sm font-medium">{entry.set_name || entry.set_code}</span>
        <span className="v2-body text-xs">{entry.owned}/{entry.total} ({pct}%)</span>
      </div>
      <div className="w-full bg-v2-bg rounded-full h-1.5">
        <div
          className="bg-v2-accent h-1.5 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
          data-testid="set-progress-bar"
        />
      </div>
    </div>
  );
}

function SkeletonCard() {
  return <div className="v2-card p-4 animate-pulse h-20" data-testid="skeleton-stat" />;
}

function SkeletonHero() {
  return (
    <div className="v2-card p-8 bg-gradient-to-br from-v2-surface to-v2-bg animate-pulse" data-testid="skeleton-hero">
      <div className="h-4 bg-v2-surface-hover rounded w-24 mb-3" />
      <div className="h-10 bg-v2-surface-hover rounded w-48" />
    </div>
  );
}

function SkeletonMovers() {
  return (
    <div className="v2-card p-6 animate-pulse" data-testid="skeleton-movers">
      <div className="h-5 bg-v2-surface-hover rounded w-28 mb-4" />
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 py-2">
          <div className="w-10 h-14 bg-v2-surface-hover rounded" />
          <div className="flex-1">
            <div className="h-4 bg-v2-surface-hover rounded w-32 mb-1" />
            <div className="h-3 bg-v2-surface-hover rounded w-12" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DashboardV2() {
  const { currency } = useCurrency();

  useEffect(() => {
    document.title = "Dashboard | TEDHC Market";
  }, []);

  const summary = useApi<CollectionSummary>(
    () => fetchCollectionSummary({ currency }),
    [currency],
    { refetchOnFocus: true },
  );

  const movers = useApi<CollectionMoversData>(
    () => fetchCollectionMovers(7, 5),
    [],
    { refetchOnFocus: true },
  );

  const portfolio = useApi<PortfolioSummary>(
    () => fetchPortfolioSummary(),
    [],
    { refetchOnFocus: true },
  );

  const setCompletion = useApi<SetCompletionEntry[]>(
    () => fetchSetCompletion(),
    [],
    { refetchOnFocus: true },
  );

  const summaryData = summary.data;
  const moversData = movers.data;
  const portfolioData = portfolio.data;
  const topSets = setCompletion.data?.slice(0, 3) ?? [];

  const totalValue = summaryData?.total_value;
  const pricedCount = summaryData?.priced_count ?? 0;
  const totalUnique = summaryData?.total_unique ?? 0;
  const coveragePct = totalUnique > 0 ? Math.round((pricedCount / totalUnique) * 100) : 0;

  const isLoading = summary.loading && !summaryData;

  return (
    <div className="font-figtree max-w-7xl mx-auto px-fluid-md py-fluid-md space-y-fluid-lg" data-testid="dashboard-v2">

      {/* Portfolio Hero */}
      {isLoading ? (
        <SkeletonHero />
      ) : (
        <div className="v2-card p-8 bg-gradient-to-br from-v2-surface to-v2-bg" data-testid="portfolio-hero">
          <p className="v2-body text-sm uppercase tracking-wider">Portfolio Value</p>
          <p className="text-4xl font-bold text-white mt-2" data-testid="portfolio-value">
            {totalValue != null
              ? formatCurrency(totalValue, currency)
              : "\u2014"}
          </p>
          {portfolioData && portfolioData.total_pnl_pct != null && (
            <p
              className={`text-sm mt-1 font-medium ${portfolioData.total_pnl_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}
              data-testid="portfolio-pnl"
            >
              {portfolioData.total_pnl_pct >= 0 ? "+" : ""}
              {portfolioData.total_pnl_pct.toFixed(1)}% overall
            </p>
          )}
        </div>
      )}

      {/* Quick Stats Row */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-fluid-sm" data-testid="stats-loading">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-fluid-sm" data-testid="stats-row">
          <StatCard label="Total Cards" value={totalUnique} testId="stat-total-cards" />
          <StatCard label="Sets" value={summaryData?.sets_count ?? 0} testId="stat-sets" />
          <StatCard label="Priced" value={pricedCount} testId="stat-priced" />
          <StatCard label="Coverage" value={`${coveragePct}%`} testId="stat-coverage" />
        </div>
      )}

      {/* Movers Section */}
      {movers.loading && !moversData ? (
        <div className="grid md:grid-cols-2 gap-fluid-md">
          <SkeletonMovers />
          <SkeletonMovers />
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-fluid-md" data-testid="movers-section">
          {/* Top Gainers */}
          <div className="v2-card p-6" data-testid="gainers-card">
            <h2 className="v2-heading text-lg mb-4">Top Gainers</h2>
            {moversData?.gainers && moversData.gainers.length > 0 ? (
              moversData.gainers.slice(0, 5).map((card) => (
                <MoverRow key={card.card_id} mover={card} type="gainer" />
              ))
            ) : (
              <p className="v2-body text-sm" data-testid="no-gainers">No movers yet</p>
            )}
          </div>

          {/* Top Losers */}
          <div className="v2-card p-6" data-testid="losers-card">
            <h2 className="v2-heading text-lg mb-4">Top Losers</h2>
            {moversData?.losers && moversData.losers.length > 0 ? (
              moversData.losers.slice(0, 5).map((card) => (
                <MoverRow key={card.card_id} mover={card} type="loser" />
              ))
            ) : (
              <p className="v2-body text-sm" data-testid="no-losers">No movers yet</p>
            )}
          </div>
        </div>
      )}

      {/* Set Completion Preview */}
      {topSets.length > 0 && (
        <div className="v2-card p-6" data-testid="set-completion-preview">
          <h2 className="v2-heading text-lg mb-4">Set Completion</h2>
          {topSets.map((entry) => (
            <SetProgressRow key={entry.set_code} entry={entry} />
          ))}
        </div>
      )}

      {/* Error / Empty handling */}
      {summary.error && !summaryData && (
        <div className="v2-card p-8 text-center" data-testid="dashboard-error">
          <p className="v2-body">Could not load collection data</p>
          <button
            onClick={() => summary.refetch()}
            className="v2-accent mt-2 hover:underline"
            data-testid="retry-button"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
