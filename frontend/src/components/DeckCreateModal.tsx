import { useState } from "react";
import { useTranslation } from "react-i18next";
import { createDeck } from "../api/decks";

interface DeckCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (deckId: number) => void;
}

export function DeckCreateModal({ isOpen, onClose, onCreated }: DeckCreateModalProps) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCreate = async () => {
    const trimmedName = name.trim();
    if (!trimmedName) return;

    setLoading(true);
    setError(null);

    const resp = await createDeck(trimmedName, description.trim() || undefined);

    setLoading(false);

    if (resp.errors.length > 0) {
      setError(resp.errors[0].message);
      return;
    }

    if (resp.data) {
      onCreated(resp.data.deck_id);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && name.trim() && !loading) {
      e.preventDefault();
      handleCreate();
    }
  };

  const inputClasses =
    "w-full px-3 py-2 rounded-md bg-slate-700 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      data-testid="deck-create-modal"
    >
      <div
        className="bg-slate-800 rounded-xl shadow-lg border border-slate-600 w-full max-w-lg mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold text-white mb-4">
          {t("decks.createTitle")}
        </h2>

        {error && (
          <div
            className="mb-4 p-3 rounded-md bg-red-900/30 border border-red-700/50 text-red-400 text-sm"
            data-testid="create-error"
          >
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">
              {t("decks.nameLabel")}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={handleKeyDown}
              className={inputClasses}
              placeholder={t("decks.namePlaceholder")}
              maxLength={200}
              autoFocus
              data-testid="create-deck-name-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">
              {t("decks.descriptionLabel")}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className={inputClasses}
              placeholder={t("decks.descriptionPlaceholder")}
              data-testid="create-deck-description-input"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            data-testid="cancel-create-btn"
            disabled={loading}
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={handleCreate}
            disabled={loading || !name.trim()}
            className="px-4 py-2 rounded-md text-sm font-medium bg-indigo-500 text-white hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
            data-testid="submit-create-btn"
          >
            {loading ? t("decks.creating") : t("decks.createButton")}
          </button>
        </div>
      </div>
    </div>
  );
}
