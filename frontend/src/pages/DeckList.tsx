import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { fetchDecks } from "../api/decks";
import { DeckImportModal } from "../components/DeckImportModal";
import type { DeckSummary } from "../types/api";

export function DeckList() {
  const { t } = useTranslation();
  const [decks, setDecks] = useState<DeckSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);
  const lastFetchedAtRef = useRef(0);

  const loadDecks = useCallback(async () => {
    setLoading(true);
    setError(null);
    const resp = await fetchDecks();
    lastFetchedAtRef.current = Date.now();
    if (resp.errors.length > 0) {
      setError(resp.errors[0].message);
    } else {
      setDecks(resp.data ?? []);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadDecks();
  }, [loadDecks]);

  // Refetch deck list when the browser tab regains focus (debounced 30s)
  useEffect(() => {
    const handler = () => {
      if (document.visibilityState !== "visible") return;
      const elapsed = Date.now() - lastFetchedAtRef.current;
      if (elapsed < 30_000) return;
      loadDecks();
    };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, [loadDecks]);

  return (
    <div data-testid="page-decks">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">{t("decks.title")}</h1>
        <button
          onClick={() => setShowImport(true)}
          className="px-4 py-2 rounded-md text-sm font-medium bg-indigo-500 text-white hover:bg-indigo-400 transition-colors shadow-md"
          data-testid="import-deck-btn"
        >
          {t("decks.importDeck")}
        </button>
      </div>

      {error && (
        <div
          className="mb-4 p-3 rounded-md bg-red-900/20 border border-red-700/50 text-red-400 text-sm"
          data-testid="deck-list-error"
        >
          {error}
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 rounded-lg bg-slate-800 animate-pulse"
              data-testid="deck-skeleton"
            />
          ))}
        </div>
      )}

      {!loading && decks.length === 0 && !error && (
        <div
          className="text-center py-12 text-slate-400"
          data-testid="deck-empty-state"
        >
          <p className="text-lg mb-2">{t("decks.noDecks")}</p>
          <p className="text-sm">
            {t("decks.noDecksHint")}
          </p>
        </div>
      )}

      {!loading && decks.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {decks.map((deck) => (
            <Link
              key={deck.id}
              to={`/decks/${deck.id}`}
              className="block p-4 rounded-lg bg-slate-800 border border-slate-600 hover:border-indigo-500/50 hover:shadow-lg transition-all duration-200"
              data-testid={`deck-card-${deck.id}`}
            >
              <h3 className="text-lg font-semibold text-white mb-1">
                {deck.name}
              </h3>
              {deck.description && (
                <p className="text-sm text-slate-400 mb-3 line-clamp-2">
                  {deck.description}
                </p>
              )}
              <div className="flex items-center gap-4 text-sm text-slate-400">
                <span data-testid="deck-card-count">
                  {t("decks.cardsCount", { count: deck.total_cards })}
                </span>
                <span data-testid="deck-unique-count">
                  {t("decks.uniqueCount", { count: deck.unique_cards })}
                </span>
                <span
                  className={
                    deck.ownership_pct === 100
                      ? "text-green-400"
                      : deck.ownership_pct > 50
                        ? "text-amber-400"
                        : "text-red-400"
                  }
                  data-testid="deck-ownership"
                >
                  {t("decks.ownershipPct", { pct: deck.ownership_pct.toFixed(0) })}
                </span>
              </div>
              {/* Value badge */}
              <div className="flex items-center gap-2 mt-2 text-sm" data-testid="deck-value-badge">
                <span className="font-semibold text-white">
                  {deck.total_value !== null
                    ? `R$ ${deck.total_value.toFixed(2)}`
                    : t("metrics.notAvailable")}
                </span>
                {deck.value_change_pct !== null && (
                  <span
                    className={`text-xs font-medium ${
                      deck.value_change_pct > 0
                        ? "text-green-400"
                        : deck.value_change_pct < 0
                          ? "text-red-400"
                          : "text-slate-400"
                    }`}
                    data-testid="deck-value-change"
                  >
                    {deck.value_change_pct > 0 ? "+" : ""}
                    {deck.value_change_pct.toFixed(1)}%
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}

      {showImport && (
        <DeckImportModal
          onClose={() => setShowImport(false)}
          onSuccess={() => {
            setShowImport(false);
            loadDecks();
          }}
        />
      )}
    </div>
  );
}
