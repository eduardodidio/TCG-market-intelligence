import { useState } from "react";
import { useTranslation } from "react-i18next";
import { importDeck } from "../api/decks";

interface DeckImportModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function DeckImportModal({ onClose, onSuccess }: DeckImportModalProps) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [format, setFormat] = useState<"text" | "csv">("text");
  const [content, setContent] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImport = async () => {
    if (!name.trim() || !content.trim()) {
      setError(t("deckImport.requiredError"));
      return;
    }

    setLoading(true);
    setError(null);

    const resp = await importDeck(
      name.trim(),
      format,
      content.trim(),
      description.trim() || undefined,
    );

    setLoading(false);

    if (resp.errors.length > 0) {
      setError(resp.errors[0].message);
      return;
    }

    onSuccess();
  };

  const inputClasses = "w-full px-3 py-2 rounded-tcg-md bg-tcg-card-alt border border-tcg-border text-white placeholder-tcg-dimmed focus:outline-none focus:ring-2 focus:ring-tcg-primary transition-colors";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      data-testid="deck-import-modal"
    >
      <div className="bg-tcg-surface rounded-tcg-xl shadow-tcg-lg border border-tcg-border w-full max-w-lg mx-4 p-6">
        <h2 className="text-xl font-bold text-white mb-4">{t("deckImport.title")}</h2>

        {error && (
          <div
            className="mb-4 p-3 rounded-tcg-md bg-red-900/30 border border-red-700/50 text-tcg-loss text-sm"
            data-testid="import-error"
          >
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-tcg-muted mb-1">
              {t("deckImport.deckName")}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputClasses}
              placeholder={t("deckImport.deckNamePlaceholder")}
              data-testid="deck-name-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-tcg-muted mb-1">
              {t("deckImport.format")}
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setFormat("text")}
                className={`px-4 py-1.5 rounded-tcg-md text-sm font-medium transition-colors ${
                  format === "text"
                    ? "bg-tcg-primary text-white shadow-tcg-glow"
                    : "bg-tcg-card text-tcg-muted hover:bg-tcg-card-alt hover:text-white"
                }`}
                data-testid="format-text-btn"
              >
                {t("deckImport.formatText")}
              </button>
              <button
                onClick={() => setFormat("csv")}
                className={`px-4 py-1.5 rounded-tcg-md text-sm font-medium transition-colors ${
                  format === "csv"
                    ? "bg-tcg-primary text-white shadow-tcg-glow"
                    : "bg-tcg-card text-tcg-muted hover:bg-tcg-card-alt hover:text-white"
                }`}
                data-testid="format-csv-btn"
              >
                {t("deckImport.formatCsv")}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-tcg-muted mb-1">
              {t("deckImport.deckList")}
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={8}
              className={`${inputClasses} font-mono text-sm`}
              placeholder={
                format === "text"
                  ? t("deckImport.textPlaceholder")
                  : t("deckImport.csvPlaceholder")
              }
              data-testid="deck-content-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-tcg-muted mb-1">
              {t("deckImport.description")}
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={inputClasses}
              placeholder={t("deckImport.descriptionPlaceholder")}
              data-testid="deck-description-input"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-tcg-md text-sm font-medium text-tcg-muted hover:text-white hover:bg-tcg-card transition-colors"
            data-testid="cancel-import-btn"
            disabled={loading}
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={handleImport}
            disabled={loading || !name.trim() || !content.trim()}
            className="px-4 py-2 rounded-tcg-md text-sm font-medium bg-tcg-primary text-white hover:bg-tcg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-tcg-glow"
            data-testid="submit-import-btn"
          >
            {loading ? t("deckImport.importing") : t("deckImport.import")}
          </button>
        </div>
      </div>
    </div>
  );
}
