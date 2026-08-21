import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDecks } from "../api/decks";
import { DeckImportModal } from "../components/DeckImportModal";
import type { DeckSummary } from "../types/api";

export function DeckList() {
  const [decks, setDecks] = useState<DeckSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);

  const loadDecks = useCallback(async () => {
    setLoading(true);
    setError(null);
    const resp = await fetchDecks();
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

  return (
    <div data-testid="page-decks">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">My Decks</h1>
        <button
          onClick={() => setShowImport(true)}
          className="px-4 py-2 rounded text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-500 transition-colors"
          data-testid="import-deck-btn"
        >
          Import Deck
        </button>
      </div>

      {error && (
        <div
          className="mb-4 p-3 rounded bg-red-900/50 text-red-300 text-sm"
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
          <p className="text-lg mb-2">No decks yet</p>
          <p className="text-sm">
            Click &quot;Import Deck&quot; to add your first deck.
          </p>
        </div>
      )}

      {!loading && decks.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {decks.map((deck) => (
            <Link
              key={deck.id}
              to={`/decks/${deck.id}`}
              className="block p-4 rounded-lg bg-slate-800 border border-slate-700 hover:border-indigo-500 transition-colors"
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
              <div className="flex items-center gap-4 text-sm text-slate-300">
                <span data-testid="deck-card-count">
                  {deck.total_cards} cards
                </span>
                <span data-testid="deck-unique-count">
                  {deck.unique_cards} unique
                </span>
                <span
                  className={
                    deck.ownership_pct === 100
                      ? "text-green-400"
                      : deck.ownership_pct > 50
                        ? "text-yellow-400"
                        : "text-red-400"
                  }
                  data-testid="deck-ownership"
                >
                  {deck.ownership_pct.toFixed(0)}% owned
                </span>
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
