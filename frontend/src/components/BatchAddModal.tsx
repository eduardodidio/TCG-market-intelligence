import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { addBatchEntries, parseBatchText } from "../api/collection";
import { BatchPreviewTable, type ParsedEntry } from "./BatchPreviewTable";
import { FormatHelpSection } from "./FormatHelpSection";

const MAX_LINES = 500;

interface BatchAddModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type ModalState = "input" | "preview" | "result";

interface BatchResult {
  added: number;
  errors: { line: number; text: string; error: string }[];
}

export function BatchAddModal({ isOpen, onClose, onSuccess }: BatchAddModalProps) {
  const { t } = useTranslation();
  const [state, setState] = useState<ModalState>("input");
  const [text, setText] = useState("");
  const [entries, setEntries] = useState<ParsedEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BatchResult | null>(null);

  const lineCount = text.split("\n").filter((l) => l.trim().length > 0).length;
  const overLimit = lineCount > MAX_LINES;

  const handlePreview = useCallback(async () => {
    if (!text.trim() || overLimit) return;
    setLoading(true);
    setError(null);

    const resp = await parseBatchText(text.trim());
    setLoading(false);

    if (resp.errors.length > 0) {
      setError(resp.errors[0].message);
      return;
    }

    if (resp.data) {
      setEntries(resp.data.entries);
      setState("preview");
    }
  }, [text, overLimit]);

  const handleRemoveEntry = useCallback((lineNumber: number) => {
    setEntries((prev) => prev.filter((e) => e.line_number !== lineNumber));
  }, []);

  const handleUpdateEntry = useCallback((lineNumber: number, field: string, value: string | number) => {
    setEntries((prev) =>
      prev.map((e) =>
        e.line_number === lineNumber ? { ...e, [field]: value } : e,
      ),
    );
  }, []);

  const validEntries = entries.filter((e) => !e.error);

  const handleAdd = useCallback(async () => {
    if (validEntries.length === 0) return;
    setLoading(true);
    setError(null);

    const body = validEntries.map((e) => ({
      name_en: e.name,
      set_code: e.set_code || undefined,
      quantity: e.quantity,
      quality: e.quality || undefined,
      language: e.language || undefined,
      extras: e.extras || undefined,
    }));

    const resp = await addBatchEntries(body);
    setLoading(false);

    if (resp.errors.length > 0 && !resp.data) {
      setError(resp.errors[0].message);
      return;
    }

    if (resp.data) {
      setResult(resp.data);
      setState("result");
    }
  }, [validEntries]);

  const handleClose = useCallback(() => {
    if (result && result.added > 0) {
      onSuccess();
    }
    // Reset state
    setState("input");
    setText("");
    setEntries([]);
    setError(null);
    setResult(null);
    onClose();
  }, [result, onSuccess, onClose]);

  const handleBackToInput = useCallback(() => {
    setState("input");
    setError(null);
  }, []);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      data-testid="batch-add-modal"
    >
      <div className="bg-slate-800 rounded-xl shadow-lg border border-slate-600 w-full max-w-2xl mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold text-white mb-4">{t("batchAdd.title")}</h2>

        {error && (
          <div
            className="mb-4 p-3 rounded-md bg-red-900/30 border border-red-700/50 text-red-400 text-sm"
            data-testid="batch-error"
          >
            {error}
          </div>
        )}

        {/* INPUT STATE */}
        {state === "input" && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">
                {t("batchAdd.pasteLabel")}
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={10}
                className="w-full px-3 py-2 rounded-md bg-slate-700 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-colors font-mono text-sm"
                placeholder={t("batchAdd.placeholder")}
                data-testid="batch-textarea"
              />
              <div className="flex items-center justify-between mt-1">
                <FormatHelpSection />
                <span
                  className={`text-xs ${overLimit ? "text-red-400" : "text-slate-500"}`}
                  data-testid="line-count"
                >
                  {lineCount} / {MAX_LINES} {t("batchAdd.lines")}
                </span>
              </div>
              {overLimit && (
                <p className="text-xs text-red-400 mt-1" data-testid="over-limit-warning">
                  {t("batchAdd.overLimitWarning", { max: MAX_LINES })}
                </p>
              )}
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                data-testid="batch-cancel-btn"
                disabled={loading}
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                onClick={handlePreview}
                disabled={loading || !text.trim() || overLimit}
                className="px-4 py-2 rounded-md text-sm font-medium bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
                data-testid="batch-preview-btn"
              >
                {loading ? t("common.loading") : t("batchAdd.preview")}
              </button>
            </div>
          </div>
        )}

        {/* PREVIEW STATE */}
        {state === "preview" && (
          <div className="space-y-4">
            <BatchPreviewTable
              entries={entries}
              onRemove={handleRemoveEntry}
              onUpdateEntry={handleUpdateEntry}
            />

            <div className="flex justify-between gap-3">
              <button
                type="button"
                onClick={handleBackToInput}
                className="px-4 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                data-testid="batch-back-btn"
              >
                {t("common.back")}
              </button>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                  data-testid="batch-cancel-btn"
                  disabled={loading}
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="button"
                  onClick={handleAdd}
                  disabled={loading || validEntries.length === 0}
                  className="px-4 py-2 rounded-md text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
                  data-testid="batch-add-btn"
                >
                  {loading
                    ? t("common.loading")
                    : t("batchAdd.addNCards", { count: validEntries.length })}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* RESULT STATE */}
        {state === "result" && result && (
          <div className="space-y-4">
            <div className="p-4 rounded-md bg-emerald-900/20 border border-emerald-700/50" data-testid="batch-result">
              <p className="text-emerald-400 font-medium">
                {t("batchAdd.resultAdded", { count: result.added })}
              </p>
              {result.errors.length > 0 && (
                <div className="mt-3">
                  <p className="text-red-400 text-sm font-medium mb-1">
                    {t("batchAdd.resultErrors", { count: result.errors.length })}
                  </p>
                  <ul className="text-xs text-red-300 space-y-1 max-h-32 overflow-y-auto">
                    {result.errors.map((err) => (
                      <li key={err.line}>
                        <span className="text-slate-500">L{err.line}:</span> {err.text} - {err.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 rounded-md text-sm font-medium bg-cyan-600 text-white hover:bg-cyan-500 transition-colors shadow-md"
                data-testid="batch-close-btn"
              >
                {t("batchAdd.close")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
