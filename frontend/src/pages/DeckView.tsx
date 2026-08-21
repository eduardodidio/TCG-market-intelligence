import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { deleteDeck, fetchDeck } from "../api/decks";
import { DeckCardTile } from "../components/DeckCardTile";
import type { DeckDetail } from "../types/api";

export function DeckView() {
  const { t } = useTranslation();
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
      setError(err instanceof Error ? err.message : t("decks.failedDelete"));
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

      {/* Card Grid */}
      {deck.cards.length === 0 ? (
        <p className="text-slate-400 text-center py-8" data-testid="deck-no-cards">
          {t("decks.noCards")}
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
