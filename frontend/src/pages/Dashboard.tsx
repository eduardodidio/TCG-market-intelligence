import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { fetchMarketStats, fetchMovers } from "../api/market";
import { fetchCollectionHealth } from "../api/collect";
import { fetchCollectionSummary } from "../api/collection";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency, formatDate } from "../utils/format";
import { KpiCard } from "../components/KpiCard";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
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
  const { t } = useTranslation();

  useEffect(() => {
    document.title = `${t("nav.dashboard")} | TCG Market`;
  }, [t]);

  const { currency } = useCurrency();

  const stats = useApi<MarketStats>(() => fetchMarketStats({ currency }), [currency]);
  const movers = useApi<MoversResponse>(() =>
    fetchMovers({ period: "30d", limit: "5", currency }),
    [currency],
  );
  const health = useApi<CollectionHealth>(() => fetchCollectionHealth());
  const collectionSummary = useApi<CollectionSummary>(() =>
    fetchCollectionSummary({ currency }),
    [currency],
  );

  const loading = stats.loading || movers.loading;
  const error = stats.error || movers.error;

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
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-white">{t("dashboard.title")}</h1>
          {freshnessIndicator}
        </div>
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonKpi key={i} />
          ))}
        </div>
        <h2 className="mb-4 text-xl font-semibold text-white">{t("dashboard.marketOverview")}</h2>
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
          <h1 className="text-2xl font-bold text-white">{t("dashboard.title")}</h1>
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
        <h1 className="text-2xl font-bold text-white">{t("collection.title")}</h1>
        {freshnessIndicator}
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

      {/* Market Overview section */}
      <h2 className="mb-4 text-xl font-semibold text-white">{t("dashboard.marketOverview")}</h2>

      {hasMarketData ? (
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4" data-testid="market-kpis">
          <KpiCard
            title={t("dashboard.totalCards")}
            value={String(marketStats?.total_cards ?? 0)}
            subtitle={t("dashboard.cardsTracked")}
          />
          <KpiCard
            title={t("dashboard.totalObservations")}
            value={String(marketStats?.total_observations ?? 0)}
            subtitle={t("dashboard.pricePoints")}
          />
          <KpiCard
            title={t("dashboard.averagePrice")}
            value={formatCurrency(marketStats?.avg_price ?? null, currency)}
            subtitle={t("dashboard.acrossAllCards")}
          />
          <KpiCard
            title={t("dashboard.dataRange")}
            value={dateRange}
            subtitle={t("dashboard.collectionPeriod")}
          />
        </div>
      ) : (
        <div className="mb-8" data-testid="market-empty">
          <EmptyState message={t("dashboard.emptyMarket")} />
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
            <EmptyState message={t("dashboard.emptyMovers")} />
          </div>
        )
      )}
    </div>
  );
}
