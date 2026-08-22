import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { fetchMovers } from "../api/market";
import { useCurrency } from "../hooks/useCurrency";
import { MoversTable } from "../components/MoversTable";
import { ErrorBanner } from "../components/ErrorBanner";
import { EmptyState } from "../components/EmptyState";
import { PeriodSelector } from "../components/PeriodSelector";
import { SkeletonTable } from "../components/Skeleton";
import type { MoversResponse } from "../types/api";

const PERIODS = ["7d", "30d", "90d"] as const;
type Period = (typeof PERIODS)[number];

const LIMITS = ["10", "25", "50"] as const;

export function MarketMovers() {
  const { t } = useTranslation();

  useEffect(() => {
    document.title = `${t("market.title")} | TCG Market`;
  }, [t]);

  const { currency } = useCurrency();
  const [period, setPeriod] = useState<Period>("30d");
  const [limit, setLimit] = useState<string>("25");

  const { data, loading, error, refetch } = useApi<MoversResponse>(
    () => fetchMovers({ period, limit, currency }),
    [period, limit, currency],
  );

  return (
    <div data-testid="page-market-movers">
      <h1 className="mb-6 text-2xl font-bold text-white">{t("market.title")}</h1>

      {/* Controls row */}
      <div className="mb-6 flex flex-wrap items-center gap-4">
        {/* Period selector */}
        <PeriodSelector value={period} onChange={(p) => setPeriod(p as Period)} />

        {/* Limit selector */}
        <select
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          aria-label={t("market.resultsLimit")}
          className="rounded-md bg-slate-800 px-3 py-2 text-sm text-slate-400 border border-slate-600 focus:outline-none focus:border-indigo-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {LIMITS.map((l) => (
            <option key={l} value={l}>
              {t("market.topN", { n: l })}
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
        <EmptyState message={t("market.emptyMovers")} />
      )}

      {/* Tables */}
      {!loading && !error && data && (data.gainers.length > 0 || data.losers.length > 0) && (
        <div className="grid gap-6 lg:grid-cols-2">
          <MoversTable
            entries={data.gainers}
            title={t("market.topGainers")}
            type="gainers"
          />
          <MoversTable
            entries={data.losers}
            title={t("market.topLosers")}
            type="losers"
          />
        </div>
      )}
    </div>
  );
}
