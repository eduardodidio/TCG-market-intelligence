import { useState } from "react";
import { useTranslation } from "react-i18next";
import { importDeck } from "../api/decks";
import type { DeckImportResult } from "../types/api";

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
  const [result, setResult] = useState<DeckImportResult | null>(null);

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

    if (resp.data) {
      setResult(resp.data);
    } else {
      onSuccess();
    }
  };

  const handleDone = () => {
    onSuccess();
  };

  const inputClasses = "w-full px-3 py-2 rounded-md bg-slate-700 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors";

  // Summary view after successful import
  if (result) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        data-testid="deck-import-modal"
      >
        <div className="bg-slate-800 rounded-xl shadow-lg border border-slate-600 w-full max-w-lg mx-4 p-6">
          <h2 className="text-xl font-bold text-white mb-4">{t("deckImport.importComplete")}</h2>

          <div className="space-y-3 mb-6" data-testid="import-summary">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">{t("deckImport.summaryName")}</span>
              <span className="text-white font-medium">{result.name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">{t("deckImport.summaryImported")}</span>
              <span className="text-white font-medium">{result.cards_imported}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">{t("deckImport.summaryLinked")}</span>
              <span className="text-green-400 font-medium">{result.cards_linked}</span>
            </div>
            {result.cards_imported > result.cards_linked && (
              <p className="text-xs text-amber-400 mt-2">
                {t("deckImport.summaryUnlinkedHint", {
                  count: result.cards_imported - result.cards_linked,
                })}
              </p>
            )}
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleDone}
              className="px-4 py-2 rounded-md text-sm font-medium bg-indigo-500 text-white hover:bg-indigo-400 transition-colors shadow-md"
              data-testid="import-done-btn"
            >
              {t("common.viewAll")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      data-testid="deck-import-modal"
    >
      <div className="bg-slate-800 rounded-xl shadow-lg border border-slate-600 w-full max-w-lg mx-4 p-6">
        <h2 className="text-xl font-bold text-white mb-4">{t("deckImport.title")}</h2>

        {error && (
          <div
            className="mb-4 p-3 rounded-md bg-red-900/30 border border-red-700/50 text-red-400 text-sm"
            data-testid="import-error"
          >
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">
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
            <label className="block text-sm font-medium text-slate-400 mb-1">
              {t("deckImport.format")}
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setFormat("text")}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  format === "text"
                    ? "bg-indigo-500 text-white shadow-md"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
                }`}
                data-testid="format-text-btn"
              >
                {t("deckImport.formatText")}
              </button>
              <button
                onClick={() => setFormat("csv")}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  format === "csv"
                    ? "bg-indigo-500 text-white shadow-md"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
                }`}
                data-testid="format-csv-btn"
              >
                {t("deckImport.formatCsv")}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">
              {t("deckImport.deckList")}
            </label>
            <p className="text-xs text-slate-500 mb-1" data-testid="format-help">
              {format === "text"
                ? t("deckImport.textFormatHelp")
                : t("deckImport.csvFormatHelp")}
            </p>
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
            <label className="block text-sm font-medium text-slate-400 mb-1">
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
            className="px-4 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            data-testid="cancel-import-btn"
            disabled={loading}
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={handleImport}
            disabled={loading || !name.trim() || !content.trim()}
            className="px-4 py-2 rounded-md text-sm font-medium bg-indigo-500 text-white hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
            data-testid="submit-import-btn"
          >
            {loading ? t("deckImport.importing") : t("deckImport.import")}
          </button>
        </div>
      </div>
    </div>
  );
}
