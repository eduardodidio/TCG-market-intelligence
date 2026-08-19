import { useEffect, useState } from "react";
import { useApi } from "../hooks/useApi";
import { fetchMovers } from "../api/market";
import { MoversTable } from "../components/MoversTable";
import { ErrorBanner } from "../components/ErrorBanner";
import { EmptyState } from "../components/EmptyState";
import { SkeletonTable } from "../components/Skeleton";
import type { MoversResponse } from "../types/api";

const PERIODS = ["7d", "30d", "90d"] as const;
type Period = (typeof PERIODS)[number];

const LIMITS = ["10", "25", "50"] as const;

export function MarketMovers() {
  useEffect(() => {
    document.title = "Market Movers | TCG Market";
  }, []);

  const [period, setPeriod] = useState<Period>("7d");
  const [limit, setLimit] = useState<string>("25");

  const { data, loading, error, refetch } = useApi<MoversResponse>(
    () => fetchMovers({ period, limit }),
    [period, limit],
  );

  return (
    <div data-testid="page-market-movers">
      <h1 className="mb-6 text-2xl font-bold text-white">Market Movers</h1>

      {/* Controls row */}
      <div className="mb-6 flex flex-wrap items-center gap-4">
        {/* Period selector */}
        <div className="flex rounded-lg overflow-hidden" role="group" aria-label="Period selector">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                p === period
                  ? "bg-cyan-500 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Limit selector */}
        <select
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          aria-label="Results limit"
          className="rounded-lg bg-slate-700 px-3 py-2 text-sm text-slate-300 border border-slate-600 focus:outline-none focus:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {LIMITS.map((l) => (
            <option key={l} value={l}>
              Top {l}
            </option>
          ))}
        </select>
      </div>

      {/* Loading state — skeleton tables */}
      {loading && (
        <div className="grid gap-6 lg:grid-cols-2" data-testid="skeleton-movers">
          <SkeletonTable rows={5} />
          <SkeletonTable rows={5} />
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <ErrorBanner message={error} variant="full" onRetry={refetch} />
      )}

      {/* Empty state */}
      {!loading && !error && data && data.gainers.length === 0 && data.losers.length === 0 && (
        <EmptyState message="No movers data available for this period." />
      )}

      {/* Tables */}
      {!loading && !error && data && (data.gainers.length > 0 || data.losers.length > 0) && (
        <div className="grid gap-6 lg:grid-cols-2">
          <MoversTable
            entries={data.gainers}
            title="Top Gainers"
            type="gainers"
          />
          <MoversTable
            entries={data.losers}
            title="Top Losers"
            type="losers"
          />
        </div>
      )}
    </div>
  );
}
