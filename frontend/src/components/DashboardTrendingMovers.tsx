import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchTrending } from "../api/trending";
import type { CollectionMoverData } from "../api/collection";
import type { TrendingResponse } from "../types/api";
import { useCardName } from "../hooks/useCardName";
import { ErrorBanner } from "./ErrorBanner";
import { MoverRow } from "./CollectionMovers";

interface DashboardTrendingMoversProps {
  direction: "gainers" | "losers";
  period: string;
  currency: string;
  limit?: number;
  collectionOnly?: boolean;
}

export function DashboardTrendingMovers({
  direction,
  period,
  currency,
  limit = 10,
  collectionOnly = false,
}: DashboardTrendingMoversProps) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();

  const [data, setData] = useState<CollectionMoverData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);

    const params: Record<string, string> = {
      period,
      currency,
      limit: String(limit),
    };
    if (collectionOnly) params.collection_only = "true";

    fetchTrending(direction, params)
      .then((res) => {
        if (res.data) {
          const mapped: CollectionMoverData[] = res.data.cards.map((c) => ({
            card_id: c.card_id,
            card_name: getCardName(c.name_en, c.name_pt),
            set_code: c.set_code,
            image_uri: c.image_url,
            price_start: c.price_start,
            price_end: c.price_end,
            change_abs: c.change_abs,
            change_pct: c.change_pct,
          }));
          setData(mapped);
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  }, [direction, period, currency, limit, collectionOnly, getCardName]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const type = direction === "gainers" ? "gainer" : "loser";
  const headerColor =
    direction === "gainers" ? "text-emerald-400" : "text-red-400";
  const titleKey =
    direction === "gainers" ? "movers.gainers" : "movers.losers";

  if (loading) {
    return (
      <div
        className="animate-pulse bg-slate-700/50 rounded-lg h-48"
        data-testid={`dashboard-trending-${direction}-loading`}
      />
    );
  }

  if (error) {
    return (
      <div data-testid={`dashboard-trending-${direction}-error`}>
        <ErrorBanner message={error} onRetry={fetchData} />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div
        className="bg-slate-800 rounded-lg p-4 border border-slate-600 text-center"
        data-testid={`dashboard-trending-${direction}-empty`}
      >
        <p className="text-sm text-slate-400">{t("movers.noData")}</p>
      </div>
    );
  }

  return (
    <div
      className="bg-slate-800 rounded-lg p-4 border border-slate-600"
      data-testid={`dashboard-trending-${direction}`}
    >
      <h4 className={`text-sm font-semibold ${headerColor} mb-2`}>
        {t(titleKey)}
      </h4>
      {data.map((m) => (
        <MoverRow key={m.card_id} mover={m} type={type} />
      ))}
    </div>
  );
}
