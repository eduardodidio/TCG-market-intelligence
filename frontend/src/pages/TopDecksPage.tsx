import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { fetchDeckRanking } from "../api/deckRanking";
import { Breadcrumb } from "../components/Breadcrumb";
import { DeckSparkline } from "../components/DeckSparkline";
import type { DeckRankingEntry, DeckRankingResponse } from "../types/api";

const SORT_OPTIONS = [
  { value: "total_value", labelKey: "topDecks.sortByValue" },
  { value: "value_change_pct", labelKey: "topDecks.sortByChange" },
  { value: "card_count", labelKey: "topDecks.sortByCards" },
] as const;

const PERIOD_OPTIONS = ["7d", "30d", "90d"] as const;

const PAGE_SIZE = 20;

export function TopDecksPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();

  const sortBy = searchParams.get("sort_by") || "total_value";
  const period = searchParams.get("period") || "30d";

  const [data, setData] = useState<DeckRankingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [allDecks, setAllDecks] = useState<DeckRankingEntry[]>([]);

  const loadDecks = useCallback(
    async (currentOffset: number, append: boolean) => {
      setLoading(true);
      setError(null);
      const resp = await fetchDeckRanking({
        sort_by: sortBy,
        period,
        limit: PAGE_SIZE,
        offset: currentOffset,
      });
      if (resp.errors.length > 0) {
        setError(resp.errors[0].message);
      } else if (resp.data) {
        setData(resp.data);
        if (append) {
          setAllDecks((prev) => [...prev, ...resp.data!.decks]);
        } else {
          setAllDecks(resp.data.decks);
        }
      }
      setLoading(false);
    },
    [sortBy, period],
  );

  useEffect(() => {
    setOffset(0);
    loadDecks(0, false);
  }, [loadDecks]);

  const handleLoadMore = () => {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    loadDecks(newOffset, true);
  };

  const updateParam = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    params.set(key, value);
    setSearchParams(params);
  };

  return (
    <div data-testid="page-top-decks">
      <Breadcrumb
        items={[
          { label: t("nav.myDecks"), to: "/decks" },
          { label: t("nav.topDecks") },
        ]}
      />
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
        <h1 className="text-2xl font-bold text-white">{t("topDecks.title")}</h1>
        <div className="flex items-center gap-3">
          {/* Sort dropdown */}
          <select
            value={sortBy}
            onChange={(e) => updateParam("sort_by", e.target.value)}
            className="bg-slate-800 border border-slate-600 text-white text-sm rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-cyan-400"
            data-testid="sort-select"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {t(opt.labelKey)}
              </option>
            ))}
          </select>

          {/* Period pills */}
          <div className="flex gap-1" data-testid="period-selector">
            {PERIOD_OPTIONS.map((p) => (
              <button
                key={p}
                onClick={() => updateParam("period", p)}
                className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                  period === p
                    ? "bg-cyan-500 text-white"
                    : "bg-slate-800 text-slate-400 hover:text-white"
                }`}
                data-testid={`period-${p}`}
              >
                {t(`topDecks.period${p.toUpperCase().replace("D", "d")}`)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          className="mb-4 p-3 rounded-md bg-red-900/20 border border-red-700/50 text-red-400 text-sm"
          data-testid="ranking-error"
        >
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && allDecks.length === 0 && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 rounded-lg bg-slate-800 animate-pulse"
              data-testid="ranking-skeleton"
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && allDecks.length === 0 && !error && (
        <div
          className="text-center py-12 text-slate-400"
          data-testid="ranking-empty"
        >
          <p className="text-lg mb-2">{t("topDecks.noDecks")}</p>
          <p className="text-sm">{t("topDecks.noDecksHint")}</p>
        </div>
      )}

      {/* Ranked list */}
      {allDecks.length > 0 && (
        <div className="space-y-2" data-testid="ranking-list">
          {allDecks.map((deck, idx) => (
            <Link
              key={deck.id}
              to={`/decks/${deck.id}`}
              className="flex items-center gap-4 p-4 rounded-lg bg-slate-800 border border-slate-600 hover:border-cyan-500/50 hover:shadow-lg transition-all duration-200"
              data-testid={`ranking-entry-${deck.id}`}
            >
              {/* Rank number */}
              <span className="text-2xl font-bold text-slate-500 w-8 text-center" data-testid="rank-number">
                {idx + 1}
              </span>

              {/* Deck info */}
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-white truncate">
                  {deck.name}
                </h3>
                <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                  <span>{t("decks.cardsCount", { count: deck.total_cards })}</span>
                  <span>{t("decks.ownershipPct", { pct: deck.ownership_pct.toFixed(0) })}</span>
                  <span data-testid="priced-indicator">
                    {t("topDecks.pricedCards", {
                      priced: deck.priced_cards,
                      total: deck.priced_cards + deck.unpriced_cards,
                    })}
                  </span>
                </div>
              </div>

              {/* Sparkline */}
              <div className="hidden sm:block">
                <DeckSparkline data={deck.sparkline} />
              </div>

              {/* Value */}
              <div className="text-right min-w-[100px]">
                <p className="text-lg font-bold text-white" data-testid="deck-value">
                  {deck.total_value !== null
                    ? `${deck.currency === "USD" ? "$" : "R$"} ${deck.total_value.toFixed(2)}`
                    : t("metrics.notAvailable")}
                </p>
                {deck.value_change_pct !== null && (
                  <p
                    className={`text-sm font-medium ${
                      deck.value_change_pct > 0
                        ? "text-green-400"
                        : deck.value_change_pct < 0
                          ? "text-red-400"
                          : "text-slate-400"
                    }`}
                    data-testid="value-change"
                  >
                    {deck.value_change_pct > 0 ? "+" : ""}
                    {deck.value_change_pct.toFixed(1)}%
                  </p>
                )}
              </div>
            </Link>
          ))}

          {/* Load more */}
          {data && allDecks.length < data.total && (
            <div className="text-center pt-4">
              <button
                onClick={handleLoadMore}
                disabled={loading}
                className="px-6 py-2 rounded-md text-sm font-medium bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors disabled:opacity-50"
                data-testid="load-more-btn"
              >
                {loading ? t("common.loading") : t("topDecks.loadMore")}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
