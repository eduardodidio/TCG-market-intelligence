import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { importCollectionCsv } from "../api/collection";
import type { ImportResult } from "../types/api";
import { formatCurrency } from "../utils/format";

interface CsvImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type ModalState = "idle" | "detecting" | "detected" | "uploading" | "success" | "error";
type CurrencyChoice = "auto" | "BRL" | "USD";

interface ImportStats {
  imported: number;
  skipped: number;
  linked: number;
  total_csv_rows: number;
}

export function CsvImportModal({ isOpen, onClose, onSuccess }: CsvImportModalProps) {
  const { t } = useTranslation();
  const [state, setState] = useState<ModalState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [stats, setStats] = useState<ImportStats | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [detection, setDetection] = useState<ImportResult | null>(null);
  const [currency, setCurrency] = useState<CurrencyChoice>("auto");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0] ?? null;
      setFile(selected);
      setDetection(null);
      setCurrency("auto");
      setErrorMessage(null);

      if (!selected) {
        setState("idle");
        return;
      }

      setState("detecting");
      try {
        const result = await importCollectionCsv(selected, { dryRun: true });
        if (result.data) {
          setDetection(result.data);
          setState("detected");
        } else {
          setState("idle");
        }
      } catch {
        setState("idle");
      }
    },
    [],
  );

  const handleImport = useCallback(async () => {
    if (!file) return;
    setState("uploading");
    setErrorMessage(null);

    try {
      const result = await importCollectionCsv(file, { currency });
      if (result.errors && result.errors.length > 0) {
        setState("error");
        setErrorMessage(result.errors[0].message || t("collection.importCsvError"));
        return;
      }
      if (result.data) {
        setStats(result.data);
        setImportResult(result.data);
        setState("success");
      }
    } catch {
      setState("error");
      setErrorMessage(t("collection.importCsvError"));
    }
  }, [file, currency, t]);

  const handleClose = useCallback(() => {
    if (state === "success") {
      onSuccess();
    }
    // Reset state
    setState("idle");
    setFile(null);
    setStats(null);
    setImportResult(null);
    setDetection(null);
    setCurrency("auto");
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClose();
  }, [state, onSuccess, onClose]);

  if (!isOpen) return null;

  const showLowConfidenceWarning =
    detection != null &&
    (detection.currency_source === "default" || detection.currency_confidence === "low");

  const exchangeRate =
    importResult?.exchange_rate != null ? Number(importResult.exchange_rate) : null;
  const priceWarnings = importResult?.price_warnings ?? [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      data-testid="csv-import-modal"
    >
      <div className="bg-slate-800 rounded-xl shadow-lg border border-slate-600 w-full max-w-md mx-4 p-6">
        <h2 className="text-xl font-bold text-white mb-4">{t("collection.importCsvTitle")}</h2>

        {/* Warning */}
        <div
          className="mb-4 p-3 rounded-md bg-amber-900/30 border border-amber-700/50 text-amber-400 text-sm"
          data-testid="csv-import-warning"
        >
          {t("collection.importCsvWarning")}
        </div>

        {/* Error */}
        {state === "error" && errorMessage && (
          <div
            className="mb-4 p-3 rounded-md bg-red-900/30 border border-red-700/50 text-red-400 text-sm"
            data-testid="csv-import-error"
          >
            {errorMessage}
          </div>
        )}

        {/* Success */}
        {state === "success" && stats && (
          <div
            className="mb-4 p-4 rounded-md bg-emerald-900/20 border border-emerald-700/50"
            data-testid="csv-import-success"
          >
            <p className="text-emerald-400 font-medium mb-2">
              {t("collection.importCsvSuccess")}
            </p>
            <p className="text-slate-300 text-sm" data-testid="csv-import-stats">
              {t("collection.importStats", {
                imported: stats.imported,
                skipped: stats.skipped,
                linked: stats.linked,
              })}
            </p>
            {importResult != null && (
              <p className="text-slate-300 text-sm mt-1" data-testid="csv-import-price-stats">
                {t("collection.importPriced", { count: importResult.priced ?? 0 })}
                {", "}
                {t("collection.importConverted", { count: importResult.converted ?? 0 })}
              </p>
            )}
            {exchangeRate != null && (importResult?.converted ?? 0) > 0 && (
              <p className="text-slate-400 text-xs mt-1" data-testid="csv-import-rate">
                {t("collection.importRate", { rate: formatCurrency(exchangeRate, "BRL") })}
              </p>
            )}
            {priceWarnings.length > 0 && (
              <div className="mt-2" data-testid="csv-import-price-warnings">
                <p className="text-amber-400 text-xs font-medium">
                  {t("collection.importPriceWarnings")}
                </p>
                <ul className="text-slate-400 text-xs list-disc list-inside">
                  {priceWarnings.slice(0, 5).map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* File input + currency selector (hidden in success state) */}
        {state !== "success" && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-400 mb-2">
              {t("collection.selectCsvFile")}
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0 file:text-sm file:font-medium
                file:bg-cyan-600 file:text-white hover:file:bg-cyan-500
                file:cursor-pointer file:transition-colors"
              data-testid="csv-file-input"
              disabled={state === "uploading"}
            />

            {file && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-slate-400 mb-1">
                  {t("collection.importCurrencyLabel")}
                </label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value as CurrencyChoice)}
                  className="block w-full rounded-md bg-slate-700 text-slate-200 text-sm px-3 py-2 border border-slate-600"
                  data-testid="csv-currency-select"
                  disabled={state === "uploading"}
                >
                  <option value="auto">
                    {t("collection.importCurrencyAuto", {
                      currency: detection?.detected_currency ?? "?",
                    })}
                  </option>
                  <option value="BRL">BRL</option>
                  <option value="USD">USD</option>
                </select>

                {state === "detecting" && (
                  <p className="text-slate-400 text-xs mt-2" data-testid="csv-currency-detecting">
                    {t("collection.importing")}
                  </p>
                )}

                {detection != null && (
                  <p className="text-slate-300 text-xs mt-2" data-testid="csv-currency-detected">
                    {t("collection.importCurrencyDetected", {
                      currency: detection.detected_currency,
                    })}
                    {" — "}
                    {t(
                      `collection.importCurrencySource.${detection.currency_source ?? "default"}`,
                    )}
                  </p>
                )}

                {showLowConfidenceWarning && (
                  <p
                    className="text-yellow-500 text-xs mt-2"
                    data-testid="csv-currency-warning"
                  >
                    {t("collection.importCurrencyLowConfidence")}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={handleClose}
            className="px-4 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
            data-testid="csv-cancel-btn"
            disabled={state === "uploading"}
          >
            {state === "success" ? t("batchAdd.close") : t("common.cancel")}
          </button>
          {state !== "success" && (
            <button
              type="button"
              onClick={handleImport}
              disabled={!file || state === "uploading"}
              className="px-4 py-2 rounded-md text-sm font-medium bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
              data-testid="csv-import-btn"
            >
              {state === "uploading" ? t("collection.importing") : t("collection.importCsv")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
