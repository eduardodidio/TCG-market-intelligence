import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  type ApplyMatch,
  type ApplyResponse,
  type ImportPreviewResponse,
  type ParsedMatch,
  applyPurchases,
  uploadForPreview,
} from "../api/purchases";
import { formatCurrency } from "../utils/format";

/* ------------------------------------------------------------------ */
/* Confidence badge                                                   */
/* ------------------------------------------------------------------ */

function ConfidenceBadge({
  confidence,
  method,
  t,
}: {
  confidence: number;
  method: string;
  t: (key: string) => string;
}) {
  const color =
    confidence >= 0.95
      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
      : confidence >= 0.85
        ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
        : "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200";
  const label =
    confidence >= 0.95
      ? t("import.confidenceExact")
      : confidence >= 0.85
        ? t("import.confidenceHigh")
        : t("import.confidencePartial");
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${color}`}
      data-testid="confidence-badge"
    >
      {label} ({(confidence * 100).toFixed(0)}%)
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Converted currency badge                                           */
/* ------------------------------------------------------------------ */

function ConvertedBadge({
  match,
  t,
}: {
  match: ParsedMatch;
  t: (key: string, opts?: Record<string, unknown>) => string;
}) {
  const original = formatCurrency(
    match.original_unit_price,
    match.original_currency,
  );
  const converted = formatCurrency(match.unit_price, "BRL");
  const title = match.exchange_rate
    ? t("purchases.convertedFrom", { original: `${original} (${match.exchange_rate})` })
    : t("purchases.convertedFrom", { original });
  return (
    <span
      className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
      data-testid="purchase-converted-badge"
      title={title}
    >
      {original} &rarr; {converted}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Page states                                                        */
/* ------------------------------------------------------------------ */

type PageState = "upload" | "preview" | "result";

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export function ImportPurchasesPage() {
  const { t } = useTranslation();
  const [state, setState] = useState<PageState>("upload");
  const [files, setFiles] = useState<File[]>([]);
  const [overwrite, setOverwrite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preview data
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [editedPrices, setEditedPrices] = useState<Record<string, string>>({});

  // Result data
  const [result, setResult] = useState<ApplyResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  /* ---- File handling ---- */

  const addFiles = useCallback((newFiles: File[]) => {
    const htmlFiles = newFiles.filter(
      (f) =>
        f.name.toLowerCase().endsWith(".html") ||
        f.name.toLowerCase().endsWith(".htm"),
    );
    if (htmlFiles.length < newFiles.length) {
      setError(t("import.onlyHtmlAccepted"));
    }
    if (htmlFiles.length > 0) {
      setFiles((prev) => [...prev, ...htmlFiles]);
      setError(null);
    }
  }, [t]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      addFiles(Array.from(e.dataTransfer.files));
    },
    [addFiles],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        addFiles(Array.from(e.target.files));
      }
    },
    [addFiles],
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  /* ---- Upload ---- */

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const data = await uploadForPreview(files, overwrite);
      setPreview(data);
      // Pre-select matches with confidence >= 0.85
      const sel: Record<string, boolean> = {};
      const prices: Record<string, string> = {};
      for (const m of data.matches) {
        sel[m.id] = m.confidence >= 0.85;
        prices[m.id] = m.unit_price;
      }
      setSelected(sel);
      setEditedPrices(prices);
      setState("preview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("import.uploadFailed"));
    } finally {
      setLoading(false);
    }
  }, [files, overwrite, t]);

  /* ---- Apply ---- */

  const handleApply = useCallback(async () => {
    if (!preview) return;
    setLoading(true);
    setError(null);
    try {
      const matches: ApplyMatch[] = preview.matches
        .filter((m) => selected[m.id] && m.collection_entry_id !== null)
        .map((m) => ({
          collection_entry_id: m.collection_entry_id!,
          acquisition_price: editedPrices[m.id] || m.unit_price,
          acquired_at: m.order_date || "",
          overwrite: m.already_has_price,
        }));
      const res = await applyPurchases(matches);
      setResult(res);
      setState("result");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("import.applyFailed"));
    } finally {
      setLoading(false);
    }
  }, [preview, selected, editedPrices, t]);

  /* ---- Select helpers ---- */

  const selectedCount = preview
    ? preview.matches.filter((m) => selected[m.id]).length
    : 0;

  const toggleAll = useCallback(
    (checked: boolean) => {
      if (!preview) return;
      const sel: Record<string, boolean> = {};
      for (const m of preview.matches) {
        sel[m.id] = checked;
      }
      setSelected(sel);
    },
    [preview],
  );

  /* ---- Reset ---- */

  const resetToUpload = useCallback(() => {
    setState("upload");
    setFiles([]);
    setPreview(null);
    setSelected({});
    setEditedPrices({});
    setResult(null);
    setError(null);
  }, []);

  /* ---------------------------------------------------------------- */
  /* Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 dark:text-slate-400 mb-4">
        <Link to="/" className="hover:underline">
          {t("import.breadcrumbHome")}
        </Link>{" "}
        &gt;{" "}
        <Link to="/collection" className="hover:underline">
          {t("import.breadcrumbCollection")}
        </Link>{" "}
        &gt; {t("import.breadcrumbImport")}
      </nav>

      <h1 className="text-2xl font-bold mb-6 dark:text-white">
        {t("import.title")}
      </h1>

      {error && (
        <div
          className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded mb-4"
          role="alert"
          data-testid="error-message"
        >
          {error}
        </div>
      )}

      {/* ==================== UPLOAD STATE ==================== */}
      {state === "upload" && (
        <div data-testid="upload-state">
          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
              dragOver
                ? "border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-900/20"
                : "border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                fileInputRef.current?.click();
              }
            }}
            data-testid="drop-zone"
          >
            <svg
              className="mx-auto h-12 w-12 text-gray-400 dark:text-slate-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
            <p className="mt-2 text-gray-600 dark:text-slate-300">
              {t("import.dropZoneText")}
            </p>
            <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
              {t("import.dropZoneHint")}
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".html,.htm"
              multiple
              className="hidden"
              onChange={handleFileInput}
              data-testid="file-input"
            />
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="mt-4 space-y-2" data-testid="file-list">
              {files.map((f, i) => (
                <div
                  key={`${f.name}-${i}`}
                  className="flex items-center justify-between bg-gray-50 dark:bg-slate-800 px-4 py-2 rounded"
                >
                  <span className="text-sm truncate dark:text-slate-200">
                    {f.name}{" "}
                    <span className="text-gray-400 dark:text-slate-500">
                      ({(f.size / 1024).toFixed(1)} KB)
                    </span>
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(i);
                    }}
                    className="text-red-500 hover:text-red-700 text-sm ml-2"
                    aria-label={`${t("import.remove")} ${f.name}`}
                  >
                    {t("import.remove")}
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Overwrite checkbox */}
          <label className="flex items-center gap-2 mt-4 text-sm dark:text-slate-300">
            <input
              type="checkbox"
              checked={overwrite}
              onChange={(e) => setOverwrite(e.target.checked)}
              data-testid="overwrite-checkbox"
            />
            {t("import.overwriteLabel")}
          </label>

          {/* Upload button */}
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || loading}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="upload-button"
          >
            {loading ? t("import.uploading") : t("import.uploadAndPreview")}
          </button>
        </div>
      )}

      {/* ==================== PREVIEW STATE ==================== */}
      {state === "preview" && preview && (
        <div data-testid="preview-state">
          {/* Summary */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded p-4 mb-4">
            <p className="font-medium dark:text-blue-200">
              {t("import.itemsParsed", { totalItems: preview.total_items_parsed, totalOrders: preview.total_orders })}
            </p>
            <p className="text-sm text-gray-600 dark:text-blue-300">
              {t("import.matchedUnmatched", { matched: preview.total_items_matched, unmatched: preview.total_items_unmatched })}
              {preview.total_sealed_skipped > 0 &&
                ` ${t("import.sealedSkipped", { count: preview.total_sealed_skipped })}`}
            </p>
          </div>

          {/* Warnings */}
          {preview.warnings.length > 0 && (
            <div
              className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded p-3 mb-4"
              data-testid="warnings-section"
            >
              <p className="font-medium text-yellow-800 dark:text-yellow-200 text-sm">
                {t("import.warnings")}
              </p>
              <ul className="list-disc list-inside text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                {preview.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Empty matches */}
          {preview.matches.length === 0 && (
            <div
              className="text-center py-12 text-gray-500 dark:text-slate-400"
              data-testid="empty-matches"
            >
              <p className="text-lg font-medium">
                {t("import.noMatchingCards")}
              </p>
              <p className="text-sm mt-1">
                {t("import.noMatchingCardsHint")}
              </p>
            </div>
          )}

          {/* Matched table */}
          {preview.matches.length > 0 && (
            <>
              <div className="flex items-center gap-3 mb-3">
                <button
                  onClick={() => toggleAll(true)}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  data-testid="select-all"
                >
                  {t("import.selectAll")}
                </button>
                <button
                  onClick={() => toggleAll(false)}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  data-testid="deselect-all"
                >
                  {t("import.deselectAll")}
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="matches-table">
                  <thead>
                    <tr className="border-b dark:border-slate-600">
                      <th scope="col" className="py-2 px-2 text-left w-8">
                        <span className="sr-only">Select</span>
                      </th>
                      <th scope="col" className="py-2 px-2 text-left">
                        {t("import.colParsedName")}
                      </th>
                      <th scope="col" className="py-2 px-2 text-left">
                        {t("import.colMatchedTo")}
                      </th>
                      <th scope="col" className="py-2 px-2 text-left">
                        {t("import.colSet")}
                      </th>
                      <th scope="col" className="py-2 px-2 text-right">
                        {t("import.colPrice")}
                      </th>
                      <th scope="col" className="py-2 px-2 text-left">
                        {t("import.colDate")}
                      </th>
                      <th scope="col" className="py-2 px-2 text-left">
                        {t("import.colStore")}
                      </th>
                      <th scope="col" className="py-2 px-2 text-center">
                        {t("import.colConfidence")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.matches.map((m) => (
                      <tr
                        key={m.id}
                        className={`border-b dark:border-slate-700 ${
                          m.confidence >= 0.95
                            ? "bg-green-50/50 dark:bg-green-900/10"
                            : m.confidence >= 0.85
                              ? "bg-yellow-50/50 dark:bg-yellow-900/10"
                              : "bg-orange-50/50 dark:bg-orange-900/10"
                        }`}
                      >
                        <td className="py-2 px-2">
                          <input
                            type="checkbox"
                            checked={!!selected[m.id]}
                            onChange={(e) =>
                              setSelected((s) => ({
                                ...s,
                                [m.id]: e.target.checked,
                              }))
                            }
                            aria-label={`Select ${m.card_name_parsed}`}
                          />
                        </td>
                        <td className="py-2 px-2 dark:text-slate-200">
                          {m.card_name_parsed}
                          {m.already_has_price && (
                            <span
                              className="ml-1 text-yellow-600 dark:text-yellow-400"
                              title={t("import.alreadyHasPrice", { price: m.current_acquisition_price })}
                              data-testid="has-price-indicator"
                            >
                              !
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-2 text-gray-600 dark:text-slate-400">
                          {m.card_name_collection || "-"}
                        </td>
                        <td className="py-2 px-2 text-gray-500 dark:text-slate-400 uppercase">
                          {m.set_code_parsed || "-"}
                        </td>
                        <td className="py-2 px-2 text-right">
                          <input
                            type="text"
                            value={editedPrices[m.id] || m.unit_price}
                            onChange={(e) =>
                              setEditedPrices((p) => ({
                                ...p,
                                [m.id]: e.target.value,
                              }))
                            }
                            className="w-20 text-right border rounded px-1 py-0.5 text-sm dark:bg-slate-700 dark:border-slate-600 dark:text-slate-200"
                            aria-label={`Price for ${m.card_name_parsed}`}
                            data-testid="price-input"
                          />
                          {m.original_currency &&
                            m.original_currency !== "BRL" && (
                              <ConvertedBadge match={m} t={t} />
                            )}
                        </td>
                        <td className="py-2 px-2 text-gray-500 dark:text-slate-400">
                          {m.order_date || "-"}
                        </td>
                        <td className="py-2 px-2 text-gray-500 dark:text-slate-400">
                          {m.store_name}
                        </td>
                        <td className="py-2 px-2 text-center">
                          <ConfidenceBadge
                            confidence={m.confidence}
                            method={m.match_method}
                            t={t}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Unmatched section */}
          {preview.unmatched.length > 0 && (
            <details className="mt-4" data-testid="unmatched-section">
              <summary className="cursor-pointer text-sm font-medium text-gray-600 dark:text-slate-400">
                {t("import.unmatchedItems", { count: preview.unmatched.length })}
              </summary>
              <div className="mt-2 space-y-1">
                {preview.unmatched.map((u, i) => (
                  <div
                    key={i}
                    className="text-sm text-gray-500 dark:text-slate-400 bg-gray-50 dark:bg-slate-800 px-3 py-1 rounded"
                  >
                    {u.card_name_parsed} (R$ {u.unit_price}) -- {u.skip_reason}
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Action buttons */}
          <div className="mt-6 flex gap-3">
            <button
              onClick={handleApply}
              disabled={selectedCount === 0 || loading}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="apply-button"
            >
              {loading
                ? t("import.applying")
                : t("import.applySelected", { count: selectedCount })}
            </button>
            <button
              onClick={resetToUpload}
              className="px-6 py-2 border border-gray-300 dark:border-slate-600 rounded text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700"
              data-testid="back-button"
            >
              {t("import.backToUpload")}
            </button>
          </div>
        </div>
      )}

      {/* ==================== RESULT STATE ==================== */}
      {state === "result" && result && (
        <div data-testid="result-state">
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded p-4 mb-4">
            <p className="font-medium text-green-800 dark:text-green-200">
              {t("import.resultApplied", { count: result.total_applied })}
            </p>
          </div>

          {result.total_skipped > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-600 dark:text-slate-400 mb-2">
                {t("import.resultSkipped", { count: result.total_skipped })}
              </p>
              <ul className="list-disc list-inside text-sm text-gray-500 dark:text-slate-400">
                {result.skipped.map((s, i) => (
                  <li key={i}>
                    {s.card_name}: {s.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={resetToUpload}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              data-testid="import-more-button"
            >
              {t("import.importMore")}
            </button>
            <Link
              to="/collection"
              className="px-6 py-2 border border-gray-300 dark:border-slate-600 rounded text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 no-underline inline-flex items-center"
            >
              {t("import.goToCollection")}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
