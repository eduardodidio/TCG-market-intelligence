import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { useCurrency } from "../hooks/useCurrency";
import { fetchMarketSummary } from "../api/market";
import { PeriodSelector } from "../components/PeriodSelector";
import { MarketSummaryKpis } from "../components/MarketSummaryKpis";
import { TrendingSection } from "../components/TrendingSection";
import { VolatileSection } from "../components/VolatileSection";
import { TopDecksPreview } from "../components/TopDecksPreview";
import type { MarketSummaryResponse } from "../types/api";

export function MarketPage() {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const [period, setPeriod] = useState("30d");

  useEffect(() => {
    document.title = `${t("marketPage.title")} | TCG Market`;
  }, [t]);

  const summary = useApi<MarketSummaryResponse>(
    () => fetchMarketSummary({ period, currency }),
    [period, currency],
  );

  return (
    <div data-testid="page-market">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <h1 className="text-2xl font-bold text-white">{t("marketPage.title")}</h1>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {/* Market Summary KPIs */}
      <MarketSummaryKpis
        data={summary.data}
        loading={summary.loading}
        currency={currency}
      />

      {/* Top Gainers */}
      <div className="mb-8" data-testid="market-trending-up">
        <TrendingSection
          direction="gainers"
          period={period}
          currency={currency}
          limit={10}
        />
      </div>

      {/* Top Losers */}
      <div className="mb-8" data-testid="market-trending-down">
        <TrendingSection
          direction="losers"
          period={period}
          currency={currency}
          limit={10}
        />
      </div>

      {/* Most Volatile */}
      <div className="mb-8">
        <VolatileSection period={period} currency={currency} />
      </div>

      {/* Top Decks by Value */}
      <div className="mb-8">
        <TopDecksPreview period={period} currency={currency} />
      </div>
    </div>
  );
}
