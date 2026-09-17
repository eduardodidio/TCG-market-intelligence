import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { fetchDecks } from "../api/decks";
import { Breadcrumb } from "../components/Breadcrumb";
import { DeckImportModal } from "../components/DeckImportModal";
import { EmptyState } from "../components/EmptyState";
import type { DeckSummary } from "../types/api";

export function DeckList() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const evaluateMode = searchParams.get("evaluate") === "true";
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
      <Breadcrumb
        items={[
          { label: t("nav.dashboard"), to: "/" },
          { label: t("nav.myDecks") },
        ]}
      />
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

      {evaluateMode && (
        <div
          className="mb-4 p-3 rounded-md bg-indigo-900/20 border border-indigo-700/50 text-indigo-300 text-sm flex items-center gap-2"
          data-testid="evaluate-banner"
        >
          <svg className="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5.24 14.26a2.25 2.25 0 00-.659 1.59v.1c0 1.243 1.007 2.25 2.25 2.25h10.338c1.243 0 2.25-1.007 2.25-2.25v-.1a2.25 2.25 0 00-.66-1.59l-3.85-3.851a2.25 2.25 0 01-.659-1.591V3.104M9.75 3h4.5" />
          </svg>
          {t("deckEval.selectDeckToEvaluate", { defaultValue: "Select a deck to evaluate" })}
        </div>
      )}

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
        <div data-testid="deck-empty-state">
          <EmptyState
            icon={
              <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
            title={t("decks.noDecks")}
            description={t("decks.noDecksHint")}
            actions={[
              { label: t("decks.importDeck"), onClick: () => setShowImport(true) },
            ]}
          />
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
              {/* Evaluate button */}
              <div className="mt-3 pt-3 border-t border-slate-700">
                <Link
                  to={`/decks/${deck.id}?tab=evaluation`}
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 transition-colors"
                  data-testid={`evaluate-deck-btn-${deck.id}`}
                >
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5.24 14.26a2.25 2.25 0 00-.659 1.59v.1c0 1.243 1.007 2.25 2.25 2.25h10.338c1.243 0 2.25-1.007 2.25-2.25v-.1a2.25 2.25 0 00-.66-1.59l-3.85-3.851a2.25 2.25 0 01-.659-1.591V3.104M9.75 3h4.5" />
                  </svg>
                  {t("deckEval.tabEvaluation", { defaultValue: "Evaluation" })}
                </Link>
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
