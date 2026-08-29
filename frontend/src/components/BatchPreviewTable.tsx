import { useTranslation } from "react-i18next";

export interface ParsedEntry {
  line_number: number;
  raw_text: string;
  quantity: number;
  name: string;
  set_code: string | null;
  quality: string | null;
  language: string | null;
  extras: string | null;
  error: string | null;
}

interface BatchPreviewTableProps {
  entries: ParsedEntry[];
  onRemove: (lineNumber: number) => void;
  onUpdateEntry: (lineNumber: number, field: string, value: string | number) => void;
}

const QUALITY_OPTIONS = ["M", "NM", "SP", "MP", "HP", "D"];
const LANGUAGE_OPTIONS = ["BR", "EN", "DE", "ES", "FR", "IT", "JP", "KO", "RU", "TW"];

export function BatchPreviewTable({ entries, onRemove, onUpdateEntry }: BatchPreviewTableProps) {
  const { t } = useTranslation();

  const validCount = entries.filter((e) => !e.error).length;
  const errorCount = entries.filter((e) => !!e.error).length;

  return (
    <div data-testid="batch-preview-table">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-slate-300" data-testid="preview-counts">
          <span className="text-emerald-400 font-medium">{validCount} {t("batchAdd.valid")}</span>
          {errorCount > 0 && (
            <>
              {" / "}
              <span className="text-red-400 font-medium">{errorCount} {t("batchAdd.errors")}</span>
            </>
          )}
        </p>
      </div>

      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-slate-400 border-b border-slate-600 sticky top-0 bg-slate-800">
            <tr>
              <th className="px-2 py-2 w-8"></th>
              <th className="px-2 py-2">{t("batchAdd.colQty")}</th>
              <th className="px-2 py-2">{t("batchAdd.colName")}</th>
              <th className="px-2 py-2">{t("batchAdd.colSet")}</th>
              <th className="px-2 py-2">{t("batchAdd.colCondition")}</th>
              <th className="px-2 py-2">{t("batchAdd.colLanguage")}</th>
              <th className="px-2 py-2">{t("batchAdd.colExtras")}</th>
              <th className="px-2 py-2 w-8"></th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr
                key={entry.line_number}
                className={`border-b border-slate-700 ${entry.error ? "bg-red-900/20" : "hover:bg-slate-700/50"}`}
                data-testid={`preview-row-${entry.line_number}`}
              >
                {/* Status icon */}
                <td className="px-2 py-1.5">
                  {entry.error ? (
                    <span
                      className="text-red-400 cursor-help"
                      title={entry.error}
                      data-testid={`error-icon-${entry.line_number}`}
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </span>
                  ) : (
                    <span className="text-emerald-400">
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                  )}
                </td>

                {/* Qty (editable) */}
                <td className="px-2 py-1.5">
                  <input
                    type="number"
                    min={1}
                    max={99}
                    value={entry.quantity}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      if (!isNaN(val) && val >= 1) {
                        onUpdateEntry(entry.line_number, "quantity", val);
                      }
                    }}
                    disabled={!!entry.error}
                    className="w-14 px-1.5 py-0.5 rounded bg-slate-700 border border-slate-600 text-white text-center text-sm disabled:opacity-50"
                    data-testid={`qty-input-${entry.line_number}`}
                  />
                </td>

                {/* Name (read-only) */}
                <td className="px-2 py-1.5 text-white font-medium truncate max-w-[200px]" title={entry.name || entry.raw_text}>
                  {entry.name || entry.raw_text}
                </td>

                {/* Set (read-only) */}
                <td className="px-2 py-1.5 text-slate-400 font-mono text-xs">
                  {entry.set_code || "-"}
                </td>

                {/* Quality (editable dropdown) */}
                <td className="px-2 py-1.5">
                  <select
                    value={entry.quality || ""}
                    onChange={(e) => onUpdateEntry(entry.line_number, "quality", e.target.value)}
                    disabled={!!entry.error}
                    className="px-1.5 py-0.5 rounded bg-slate-700 border border-slate-600 text-white text-sm disabled:opacity-50"
                    data-testid={`quality-select-${entry.line_number}`}
                  >
                    <option value="">-</option>
                    {QUALITY_OPTIONS.map((q) => (
                      <option key={q} value={q}>{q}</option>
                    ))}
                  </select>
                </td>

                {/* Language (editable dropdown) */}
                <td className="px-2 py-1.5">
                  <select
                    value={entry.language || ""}
                    onChange={(e) => onUpdateEntry(entry.line_number, "language", e.target.value)}
                    disabled={!!entry.error}
                    className="px-1.5 py-0.5 rounded bg-slate-700 border border-slate-600 text-white text-sm disabled:opacity-50"
                    data-testid={`language-select-${entry.line_number}`}
                  >
                    <option value="">-</option>
                    {LANGUAGE_OPTIONS.map((l) => (
                      <option key={l} value={l}>{l}</option>
                    ))}
                  </select>
                </td>

                {/* Extras (read-only display) */}
                <td className="px-2 py-1.5 text-slate-400 text-xs">
                  {entry.extras || "-"}
                </td>

                {/* Remove button */}
                <td className="px-2 py-1.5">
                  <button
                    type="button"
                    onClick={() => onRemove(entry.line_number)}
                    className="text-slate-500 hover:text-red-400 transition-colors"
                    title={t("batchAdd.removeRow")}
                    data-testid={`remove-row-${entry.line_number}`}
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
