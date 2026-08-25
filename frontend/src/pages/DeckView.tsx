import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { refreshCardPriceLiga } from "../api/collection";
import { fetchDeckValue } from "../api/deckRanking";
import { deleteDeck, fetchDeck } from "../api/decks";
import { Breadcrumb } from "../components/Breadcrumb";
import { DeckCardTile } from "../components/DeckCardTile";
import type { DeckDetail, DeckValueDetail } from "../types/api";

export function DeckView() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [deck, setDeck] = useState<DeckDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [valueData, setValueData] = useState<DeckValueDetail | null>(null);
  const [valuePeriod, setValuePeriod] = useState("30d");
  const [showHistory, setShowHistory] = useState(false);

  const loadDeck = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    const resp = await fetchDeck(Number(id));
    if (resp.errors.length > 0) {
      setError(resp.errors[0].message);
    } else {
      setDeck(resp.data);
    }
    setLoading(false);
  }, [id]);

  useEffect(() => {
    loadDeck();
  }, [loadDeck]);

  useEffect(() => {
    if (!id) return;
    fetchDeckValue(Number(id), valuePeriod).then((resp) => {
      if (resp.data) setValueData(resp.data);
    });
  }, [id, valuePeriod]);

  const handleDelete = async () => {
    if (!id) return;
    setDeleting(true);
    try {
      await deleteDeck(Number(id));
      navigate("/decks");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("decks.failedDelete"));
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleDeckCardRefresh = useCallback(async (entryId: number) => {
    const res = await refreshCardPriceLiga(entryId);
    if (res.data && deck) {
      setDeck({
        ...deck,
        cards: deck.cards.map((c) =>
          c.collection_entry_id === entryId
            ? { ...c, latest_price: res.data!.latest_price }
            : c,
        ),
      });
    }
  }, [deck]);

  if (loading) {
    return (
      <div data-testid="page-deck-view">
        <div className="h-8 w-48 bg-slate-800 animate-pulse rounded mb-4" />
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="aspect-[488/680] bg-slate-800 animate-pulse rounded-lg"
              data-testid="deck-view-skeleton"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="page-deck-view">
        <div
          className="p-4 rounded-md bg-red-900/20 border border-red-700/50 text-red-400"
          data-testid="deck-view-error"
        >
          {error}
        </div>
      </div>
    );
  }

  if (!deck) return null;

  return (
    <div data-testid="page-deck-view">
      <Breadcrumb
        items={[
          { label: t("decks.title"), to: "/decks" },
          { label: deck.name },
        ]}
      />

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white" data-testid="deck-title">
            {deck.name}
          </h1>
          {deck.description && (
            <p className="text-slate-400 mt-1" data-testid="deck-description">
              {deck.description}
            </p>
          )}
        </div>
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="px-3 py-1.5 rounded text-sm font-medium text-red-400 hover:bg-red-900/30 transition-colors"
          data-testid="delete-deck-btn"
        >
          {t("common.delete")}
        </button>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-6 mb-6 text-sm text-slate-400">
        <span data-testid="deck-total-cards">{t("decks.cardsCount", { count: deck.total_cards })}</span>
        <span data-testid="deck-unique-cards">{t("decks.uniqueCount", { count: deck.unique_cards })}</span>
        <span data-testid="deck-owned-cards">{t("decks.owned", { count: deck.owned_cards })}</span>
        <span
          className={
            deck.ownership_pct === 100
              ? "text-green-400 font-semibold"
              : deck.ownership_pct > 50
                ? "text-amber-400"
                : "text-red-400"
          }
          data-testid="deck-ownership-pct"
        >
          {t("decks.completePct", { pct: deck.ownership_pct.toFixed(0) })}
        </span>
      </div>

      {/* Value Summary Panel */}
      {valueData && (
        <div className="mb-6 p-4 rounded-lg bg-slate-800 border border-slate-600" data-testid="value-panel">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs text-slate-400 uppercase">{t("topDecks.totalValue")}</p>
                <p className="text-xl font-bold text-white" data-testid="deck-total-value">
                  {valueData.total_value !== null
                    ? `R$ ${valueData.total_value.toFixed(2)}`
                    : t("metrics.notAvailable")}
                </p>
              </div>
              {valueData.value_change_pct !== null && (
                <div>
                  <p className="text-xs text-slate-400 uppercase">{t("topDecks.valueChange")}</p>
                  <p
                    className={`text-lg font-semibold ${
                      valueData.value_change_pct > 0
                        ? "text-green-400"
                        : valueData.value_change_pct < 0
                          ? "text-red-400"
                          : "text-slate-400"
                    }`}
                    data-testid="deck-value-change"
                  >
                    {valueData.value_change_pct > 0 ? "+" : ""}
                    {valueData.value_change_pct.toFixed(1)}%
                  </p>
                </div>
              )}
              <div>
                <p className="text-xs text-slate-400">
                  {t("topDecks.pricedCards", {
                    priced: valueData.priced_cards,
                    total: valueData.priced_cards + valueData.unpriced_cards,
                  })}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
              data-testid="toggle-history"
            >
              {showHistory ? t("topDecks.hideHistory") : t("topDecks.showHistory")}
            </button>
          </div>

          {showHistory && (
            <div>
              {/* Period selector */}
              <div className="flex gap-1 mb-3" data-testid="value-period-selector">
                {(["7d", "30d", "90d"] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setValuePeriod(p)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      valuePeriod === p
                        ? "bg-cyan-500 text-white"
                        : "bg-slate-700 text-slate-400 hover:text-white"
                    }`}
                  >
                    {t(`topDecks.period${p.toUpperCase().replace("D", "d")}`)}
                  </button>
                ))}
              </div>

              {valueData.value_series.length > 0 ? (
                <div className="h-48" data-testid="value-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={valueData.value_series}>
                      <XAxis
                        dataKey="date"
                        tick={{ fill: "#94a3b8", fontSize: 10 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#94a3b8", fontSize: 10 }}
                        tickLine={false}
                        axisLine={false}
                        width={60}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#1e293b",
                          border: "1px solid #475569",
                          borderRadius: "0.375rem",
                        }}
                        labelStyle={{ color: "#94a3b8" }}
                      />
                      <defs>
                        <linearGradient id="deckValueGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#22d3ee"
                        fill="url(#deckValueGradient)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-slate-400 text-center py-4" data-testid="no-value-data">
                  {t("topDecks.noPriceData")}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Card Grid */}
      {deck.cards.length === 0 ? (
        <p className="text-slate-400 text-center py-8" data-testid="deck-no-cards">
          {t("decks.noCards")}
        </p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {deck.cards.map((card) => {
            if (!card.name_en && !card.card_id) {
              return (
                <div
                  key={card.id}
                  className="rounded-lg bg-slate-800 border border-slate-600/50 p-4 flex items-center justify-center aspect-[488/680]"
                  data-testid={`deck-card-missing-${card.id}`}
                >
                  <p className="text-xs text-slate-500 text-center">{t("decks.cardNotFound")}</p>
                </div>
              );
            }
            return <DeckCardTile key={card.id} card={card} onRefresh={handleDeckCardRefresh} />;
          })}
        </div>
      )}

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          data-testid="delete-confirm-modal"
        >
          <div className="bg-slate-800 rounded-xl shadow-lg border border-slate-600 p-6 mx-4 max-w-sm w-full">
            <h3 className="text-lg font-bold text-white mb-2">{t("decks.deleteTitle")}</h3>
            <p className="text-sm text-slate-400 mb-4">
              {t("decks.deleteMessage", { name: deck.name })}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 rounded text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                data-testid="cancel-delete-btn"
                disabled={deleting}
              >
                {t("common.cancel")}
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 rounded text-sm font-medium bg-red-600 text-white hover:bg-red-500 disabled:opacity-50 transition-colors"
                data-testid="confirm-delete-btn"
              >
                {deleting ? t("common.deleting") : t("common.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
