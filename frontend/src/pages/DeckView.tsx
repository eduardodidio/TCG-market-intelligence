import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { deleteDeck, fetchDeck } from "../api/decks";
import { DeckCardTile } from "../components/DeckCardTile";
import type { DeckDetail } from "../types/api";

export function DeckView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [deck, setDeck] = useState<DeckDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  const handleDelete = async () => {
    if (!id) return;
    setDeleting(true);
    try {
      await deleteDeck(Number(id));
      navigate("/decks");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete deck");
      setDeleting(false);
      setShowDeleteConfirm(false);
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
        <div
          className="p-4 rounded bg-red-900/50 text-red-300"
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
          Delete
        </button>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-6 mb-6 text-sm text-slate-300">
        <span data-testid="deck-total-cards">{deck.total_cards} cards</span>
        <span data-testid="deck-unique-cards">{deck.unique_cards} unique</span>
        <span data-testid="deck-owned-cards">{deck.owned_cards} owned</span>
        <span
          className={
            deck.ownership_pct === 100
              ? "text-green-400 font-semibold"
              : deck.ownership_pct > 50
                ? "text-yellow-400"
                : "text-red-400"
          }
          data-testid="deck-ownership-pct"
        >
          {deck.ownership_pct.toFixed(0)}% complete
        </span>
      </div>

      {/* Card Grid */}
      {deck.cards.length === 0 ? (
        <p className="text-slate-400 text-center py-8" data-testid="deck-no-cards">
          No cards in this deck.
        </p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {deck.cards.map((card) => (
            <DeckCardTile key={card.id} card={card} />
          ))}
        </div>
      )}

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          data-testid="delete-confirm-modal"
        >
          <div className="bg-slate-800 rounded-lg shadow-xl p-6 mx-4 max-w-sm w-full">
            <h3 className="text-lg font-bold text-white mb-2">Delete Deck?</h3>
            <p className="text-sm text-slate-400 mb-4">
              This will permanently delete &quot;{deck.name}&quot; and all its
              cards. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 rounded text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                data-testid="cancel-delete-btn"
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 rounded text-sm font-medium bg-red-600 text-white hover:bg-red-500 disabled:opacity-50 transition-colors"
                data-testid="confirm-delete-btn"
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
