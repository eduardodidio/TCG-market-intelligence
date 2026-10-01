import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { refreshCardPriceLiga } from "../api/collection";
import { fetchDeckValue } from "../api/deckRanking";
import { deleteDeck, fetchDeck, updateDeck } from "../api/decks";
import { BatchAddModal } from "../components/BatchAddModal";
import { Breadcrumb } from "../components/Breadcrumb";
import { DeckCardTile } from "../components/DeckCardTile";
import { DeckEvaluationPanel } from "../components/DeckEvaluationPanel";
import { ErrorBanner } from "../components/ErrorBanner";
import { GoldfishPanel } from "../components/GoldfishPanel";
import type { DeckDetail, DeckValueDetail } from "../types/api";

export function DeckView() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [deck, setDeck] = useState<DeckDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [valueData, setValueData] = useState<DeckValueDetail | null>(null);
  const [valuePeriod, setValuePeriod] = useState("30d");
  const [showHistory, setShowHistory] = useState(false);
  const [showBatchAdd, setShowBatchAdd] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [editName, setEditName] = useState("");
  const [editingDesc, setEditingDesc] = useState(false);
  const [editDesc, setEditDesc] = useState("");
  const [activeTab, setActiveTab] = useState<"cards" | "evaluation" | "goldfish">(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "evaluation") return "evaluation";
    if (tabParam === "goldfish") return "goldfish";
    return "cards";
  });

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

  const handleStartEditName = () => {
    if (deck) {
      setEditName(deck.name);
      setEditingName(true);
    }
  };

  const handleSaveName = async () => {
    if (!id || !deck) return;
    const trimmed = editName.trim();
    if (!trimmed || trimmed === deck.name) {
      setEditingName(false);
      return;
    }
    // Optimistic update
    const prevName = deck.name;
    setDeck({ ...deck, name: trimmed });
    setEditingName(false);
    const resp = await updateDeck(Number(id), { name: trimmed });
    if (resp.errors.length > 0) {
      // Revert on error
      setDeck((d) => d ? { ...d, name: prevName } : d);
    }
  };

  const handleStartEditDesc = () => {
    if (deck) {
      setEditDesc(deck.description ?? "");
      setEditingDesc(true);
    }
  };

  const handleSaveDesc = async () => {
    if (!id || !deck) return;
    const trimmed = editDesc.trim();
    if (trimmed === (deck.description ?? "")) {
      setEditingDesc(false);
      return;
    }
    // Optimistic update
    const prevDesc = deck.description;
    setDeck({ ...deck, description: trimmed || null });
    setEditingDesc(false);
    const resp = await updateDeck(Number(id), { description: trimmed || "" });
    if (resp.errors.length > 0) {
      setDeck((d) => d ? { ...d, description: prevDesc } : d);
    }
  };

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
        <ErrorBanner message={error} variant="full" onRetry={loadDeck} />
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
        <div className="flex-1 min-w-0 mr-4">
          {editingName ? (
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={handleSaveName}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSaveName();
                if (e.key === "Escape") setEditingName(false);
              }}
              className="w-full text-2xl font-bold text-white bg-slate-700 border border-slate-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              maxLength={200}
              autoFocus
              data-testid="deck-title-input"
            />
          ) : (
            <h1
              className="text-2xl font-bold text-white cursor-pointer group flex items-center gap-2"
              onClick={handleStartEditName}
              title={t("decks.editName")}
              data-testid="deck-title"
            >
              {deck.name}
              <svg
                className="h-4 w-4 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
              </svg>
            </h1>
          )}

          {editingDesc ? (
            <textarea
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              onBlur={handleSaveDesc}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSaveDesc();
                }
                if (e.key === "Escape") setEditingDesc(false);
              }}
              rows={2}
              className="w-full mt-1 text-slate-400 bg-slate-700 border border-slate-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
              autoFocus
              data-testid="deck-description-input"
            />
          ) : (
            <p
              className="text-slate-400 mt-1 cursor-pointer group/desc flex items-center gap-2 text-sm"
              onClick={handleStartEditDesc}
              title={t("decks.editDescription")}
              data-testid="deck-description"
            >
              {deck.description || (
                <span className="text-slate-500 italic">{t("decks.addDescription")}</span>
              )}
              <svg
                className="h-3.5 w-3.5 text-slate-500 opacity-0 group-hover/desc:opacity-100 transition-opacity flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
              </svg>
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
        {deck.ownership_pct < 100 && (
          <button
            onClick={() => setShowBatchAdd(true)}
            className="inline-flex items-center gap-2 rounded-md bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-400 transition-colors"
            data-testid="add-missing-cards-btn"
          >
            + {t("decks.addMissingCards")}
          </button>
        )}
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

      {/* Tab Switcher */}
      <div className="flex gap-1 mb-4" data-testid="deck-view-tabs">
        <button
          onClick={() => {
            setActiveTab("cards");
            setSearchParams((prev) => { prev.delete("tab"); return prev; }, { replace: true });
          }}
          className={`px-4 py-2 rounded-t text-sm font-medium transition-colors ${
            activeTab === "cards"
              ? "bg-slate-800 text-white border-b-2 border-cyan-500"
              : "bg-slate-900 text-slate-400 hover:text-white"
          }`}
          data-testid="tab-cards"
        >
          {t("deckEval.tabCards", { defaultValue: "Cards" })}
        </button>
        <button
          onClick={() => {
            setActiveTab("evaluation");
            setSearchParams((prev) => { prev.set("tab", "evaluation"); return prev; }, { replace: true });
          }}
          className={`px-4 py-2 rounded-t text-sm font-medium transition-colors ${
            activeTab === "evaluation"
              ? "bg-slate-800 text-white border-b-2 border-cyan-500"
              : "bg-slate-900 text-slate-400 hover:text-white"
          }`}
          data-testid="tab-evaluation"
        >
          {t("deckEval.tabEvaluation", { defaultValue: "Evaluation" })}
        </button>
        <button
          onClick={() => {
            setActiveTab("goldfish");
            setSearchParams((prev) => { prev.set("tab", "goldfish"); return prev; }, { replace: true });
          }}
          className={`px-4 py-2 rounded-t text-sm font-medium transition-colors ${
            activeTab === "goldfish"
              ? "bg-slate-800 text-white border-b-2 border-cyan-500"
              : "bg-slate-900 text-slate-400 hover:text-white"
          }`}
          data-testid="tab-goldfish"
        >
          {t("decks.goldfishTab", { defaultValue: "Goldfish" })}
        </button>
      </div>

      {/* Cards Tab */}
      {activeTab === "cards" && (
        <>
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
        </>
      )}

      {/* Evaluation Tab */}
      {activeTab === "evaluation" && (
        <DeckEvaluationPanel deckId={Number(id)} />
      )}

      {/* Goldfish Tab */}
      {activeTab === "goldfish" && (
        <GoldfishPanel deckId={Number(id)} />
      )}

      {/* Batch Add Missing Cards Modal */}
      {showBatchAdd && (
        <BatchAddModal
          isOpen={showBatchAdd}
          onClose={() => setShowBatchAdd(false)}
          onSuccess={() => {
            setShowBatchAdd(false);
            loadDeck();
          }}
          initialText={deck.cards
            .filter((c) => !c.in_collection && c.name_en)
            .map((c) => {
              const qty = c.quantity - c.owned_quantity;
              const set = c.set_code ? ` [${c.set_code}]` : "";
              return `${qty > 0 ? qty : 1} ${c.name_en}${set}`;
            })
            .join("\n")}
        />
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
