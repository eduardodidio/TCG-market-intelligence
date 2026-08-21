import { useState } from "react";
import { importDeck } from "../api/decks";

interface DeckImportModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function DeckImportModal({ onClose, onSuccess }: DeckImportModalProps) {
  const [name, setName] = useState("");
  const [format, setFormat] = useState<"text" | "csv">("text");
  const [content, setContent] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImport = async () => {
    if (!name.trim() || !content.trim()) {
      setError("Name and content are required.");
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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      data-testid="deck-import-modal"
    >
      <div className="bg-slate-800 rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
        <h2 className="text-xl font-bold text-white mb-4">Import Deck</h2>

        {error && (
          <div
            className="mb-4 p-3 rounded bg-red-900/50 text-red-300 text-sm"
            data-testid="import-error"
          >
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Deck Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded bg-slate-700 border border-slate-600 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Mono Red Burn"
              data-testid="deck-name-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Format
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setFormat("text")}
                className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                  format === "text"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                }`}
                data-testid="format-text-btn"
              >
                Text
              </button>
              <button
                onClick={() => setFormat("csv")}
                className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                  format === "csv"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                }`}
                data-testid="format-csv-btn"
              >
                CSV
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Deck List
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={8}
              className="w-full px-3 py-2 rounded bg-slate-700 border border-slate-600 text-white placeholder-slate-400 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder={
                format === "text"
                  ? "4 Lightning Bolt [LEA:161]\n20 Mountain\n# Comments start with #"
                  : "Card (EN),Edicao (Sigla),Card #,Quantidade\nLightning Bolt,lea,161,4"
              }
              data-testid="deck-content-input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Description (optional)
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 rounded bg-slate-700 border border-slate-600 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Fast aggro deck for FNM"
              data-testid="deck-description-input"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
            data-testid="cancel-import-btn"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={loading || !name.trim() || !content.trim()}
            className="px-4 py-2 rounded text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="submit-import-btn"
          >
            {loading ? "Importing..." : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
