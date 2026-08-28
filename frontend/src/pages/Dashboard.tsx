import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { fetchMarketStats } from "../api/market";
import { fetchCollectionHealth } from "../api/collect";
import { fetchCollectionSummary } from "../api/collection";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency } from "../utils/format";
import { KpiCard } from "../components/KpiCard";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
import { TrendingSection } from "../components/TrendingSection";
import { EmptyState } from "../components/EmptyState";
import { FreshnessIndicator } from "../components/FreshnessIndicator";
import { ErrorBanner } from "../components/ErrorBanner";
import { SkeletonKpi } from "../components/Skeleton";
import type {
  CollectionHealth,
  CollectionSummary,
  MarketStats,
} from "../types/api";

export function Dashboard() {
  const { t } = useTranslation();

  useEffect(() => {
    document.title = `${t("nav.dashboard")} | TCG Market`;
  }, [t]);

  const { currency } = useCurrency();

  const stats = useApi<MarketStats>(() => fetchMarketStats({ currency }), [currency]);
  const health = useApi<CollectionHealth>(() => fetchCollectionHealth());
  const collectionSummary = useApi<CollectionSummary>(() =>
    fetchCollectionSummary({ currency }),
    [currency],
  );

  const loading = stats.loading;
  const error = stats.error;

  // Collection summary is independent — never blocks dashboard rendering
  const summaryData = collectionSummary.data;
  const linkedPct =
    summaryData && summaryData.total_unique > 0
      ? Math.round((summaryData.linked_count / summaryData.total_unique) * 100)
      : 0;
  const pricedPct =
    summaryData && summaryData.total_unique > 0
      ? Math.round((summaryData.priced_count / summaryData.total_unique) * 100)
      : 0;
  const lowCoverage = linkedPct < 50;

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
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">
            {t("landing.heroTitle")}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {t("landing.heroSubtitle")}
          </p>
          {freshnessIndicator && (
            <div className="mt-2">{freshnessIndicator}</div>
          )}
        </div>
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonKpi key={i} />
          ))}
        </div>
        {/* Trending skeleton */}
        <div className="mb-8">
          <div className="animate-pulse bg-slate-700 rounded h-6 w-32 mb-4" />
          <div className="flex gap-3 overflow-hidden">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="shrink-0 w-44 h-40 rounded-lg bg-slate-800 animate-pulse" />
            ))}
          </div>
        </div>
        <div className="mb-8">
          <div className="animate-pulse bg-slate-700 rounded h-6 w-32 mb-4" />
          <div className="flex gap-3 overflow-hidden">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="shrink-0 w-44 h-40 rounded-lg bg-slate-800 animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="page-dashboard">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">
            {t("landing.heroTitle")}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {t("landing.heroSubtitle")}
          </p>
          {freshnessIndicator && (
            <div className="mt-2">{freshnessIndicator}</div>
          )}
        </div>
        <ErrorBanner
          message={error}
          variant="full"
          onRetry={() => {
            stats.refetch();
          }}
        />
      </div>
    );
  }

  const marketStats = stats.data;

  const hasMarketData = (marketStats?.total_cards ?? 0) > 0;

  return (
    <div data-testid="page-dashboard">
      {/* Hero header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">
          {t("landing.heroTitle")}
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          {t("landing.heroSubtitle")}
        </p>
        {freshnessIndicator && (
          <div className="mt-2">{freshnessIndicator}</div>
        )}
      </div>

      {/* Collection KPIs */}
      {!collectionSummary.loading && !collectionSummary.error && summaryData ? (
        <div
          className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4"
          data-testid="collection-kpis"
        >
          <KpiCard
            title={t("dashboard.collectionCards")}
            value={String(summaryData.total_unique)}
            subtitle={t("dashboard.uniqueCards")}
          />
          <KpiCard
            title={t("dashboard.totalCopies")}
            value={String(summaryData.total_cards)}
            subtitle={t("dashboard.totalQuantity")}
          />
          <KpiCard
            title={t("dashboard.estCollectionValue")}
            value={formatCurrency(summaryData.total_value, currency)}
            subtitle={t("dashboard.basedOnLatestPrices")}
            icon={<CurrencyIndicator currency={currency} size={20} />}
          />
          <div data-testid="coverage-breakdown">
            <KpiCard
              title={t("dashboard.coverage")}
              value={`${linkedPct}%`}
              subtitle={t("dashboard.coverageSubtitle", { linked: summaryData.linked_count, priced: summaryData.priced_count, pricedPct })}
            />
            {lowCoverage && (
              <p
                className="mt-2 text-xs text-amber-400"
                data-testid="low-coverage-hint"
              >
                {t("dashboard.lowCoverageHint")}
              </p>
            )}
          </div>
        </div>
      ) : !collectionSummary.loading ? (
        <div className="mb-8" data-testid="collection-empty">
          <EmptyState message={t("dashboard.emptyCollection")} />
        </div>
      ) : null}

      {/* Market summary strip */}
      {hasMarketData ? (
        <div
          className="mb-8 flex flex-wrap items-center gap-6 rounded-lg bg-slate-800 border border-slate-600 px-6 py-4"
          data-testid="market-summary-strip"
        >
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">{t("landing.cardsTracked")}</span>
            <span className="text-sm font-semibold text-white">{marketStats?.total_cards ?? 0}</span>
          </div>
          <div className="h-4 w-px bg-slate-600" aria-hidden="true" />
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">{t("landing.observations")}</span>
            <span className="text-sm font-semibold text-white">{marketStats?.total_observations ?? 0}</span>
          </div>
          <div className="h-4 w-px bg-slate-600" aria-hidden="true" />
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">{t("landing.avgPrice")}</span>
            <span className="text-sm font-semibold text-white">
              <CurrencyIndicator currency={currency} size={14} />
              {" "}{formatCurrency(marketStats?.avg_price ?? null, currency)}
            </span>
          </div>
        </div>
      ) : (
        <div className="mb-8" data-testid="market-empty">
          <EmptyState message={t("dashboard.emptyMarket")} />
        </div>
      )}

      {/* Trending: gainers + losers side by side */}
      <div className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-6" data-testid="trending-grid">
        <div data-testid="landing-trending-up">
          <TrendingSection
            direction="gainers"
            period="30d"
            currency={currency}
            limit={10}
            variant="list"
          />
        </div>
        <div data-testid="landing-trending-down">
          <TrendingSection
            direction="losers"
            period="30d"
            currency={currency}
            limit={10}
            variant="list"
          />
        </div>
      </div>

      {/* View All link */}
      <div className="text-center" data-testid="trending-view-all">
        <Link
          to="/market/trending"
          className="inline-flex items-center gap-1 text-sm font-medium text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {t("common.viewAll")}
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
    </div>
  );
}
