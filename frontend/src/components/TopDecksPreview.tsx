import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useApi } from "../hooks/useApi";
import { apiGet } from "../api/client";
import { formatCurrency } from "../utils/format";
import { DeckSparkline } from "./DeckSparkline";
import { SkeletonTable } from "./Skeleton";
import type { ApiResponse, DeckRankingResponse } from "../types/api";

interface TopDecksPreviewProps {
  period: string;
  currency: string;
}

function fetchDeckRanking(
  params: Record<string, string>,
): Promise<ApiResponse<DeckRankingResponse>> {
  return apiGet<DeckRankingResponse>("/api/v1/decks/ranking", params);
}

export function TopDecksPreview({ period, currency }: TopDecksPreviewProps) {
  const { t } = useTranslation();

  const { data, loading, error } = useApi<DeckRankingResponse>(
    () => fetchDeckRanking({ limit: "5", sort_by: "total_value", period, currency }),
    [period, currency],
  );

  // Graceful degradation: hide on error or empty
  if (error || (!loading && (!data || data.decks.length === 0))) {
    return null;
  }

  if (loading) {
    return (
      <section data-testid="top-decks-preview">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white">
            {t("marketPage.section.topDecks")}
          </h2>
        </div>
        <SkeletonTable rows={5} />
      </section>
    );
  }

  return (
    <section data-testid="top-decks-preview">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-white">
          {t("marketPage.section.topDecks")}
        </h2>
        <Link
          to="/decks/ranking"
          className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {t("marketPage.viewAll")}
        </Link>
      </div>
      <div className="rounded-lg bg-slate-800 border border-slate-700 divide-y divide-slate-700">
        {data!.decks.map((deck, idx) => {
          const changePct = deck.value_change_pct;
          const changeColor = changePct != null && changePct > 0
            ? "text-emerald-400"
            : changePct != null && changePct < 0
              ? "text-red-400"
              : "text-slate-400";
          const changeSign = changePct != null && changePct > 0 ? "+" : "";

          return (
            <div key={deck.id} className="flex items-center gap-3 px-4 py-3">
              <span className="text-sm font-bold text-slate-500 w-6 text-center">
                {idx + 1}
              </span>
              <div className="flex-1 min-w-0">
                <Link
                  to={`/decks/${deck.id}`}
                  className="text-sm font-medium text-white hover:text-cyan-400 transition-colors truncate block"
                >
                  {deck.name}
                </Link>
              </div>
              <div className="w-16 h-8 flex-shrink-0">
                <DeckSparkline data={deck.sparkline} width={64} height={32} />
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-sm font-semibold text-white">
                  {formatCurrency(deck.total_value, currency)}
                </div>
                {changePct != null && (
                  <div className={`text-xs ${changeColor}`}>
                    {changeSign}{changePct.toFixed(1)}%
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
