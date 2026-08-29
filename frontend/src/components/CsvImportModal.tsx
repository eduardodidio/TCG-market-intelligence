import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { importCollectionCsv } from "../api/collection";

interface CsvImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type ModalState = "idle" | "uploading" | "success" | "error";

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
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setState("idle");
    setErrorMessage(null);
  }, []);

  const handleImport = useCallback(async () => {
    if (!file) return;
    setState("uploading");
    setErrorMessage(null);

    try {
      const result = await importCollectionCsv(file);
      if (result.errors && result.errors.length > 0) {
        setState("error");
        setErrorMessage(result.errors[0].message || t("collection.importCsvError"));
        return;
      }
      if (result.data) {
        setStats(result.data);
        setState("success");
      }
    } catch {
      setState("error");
      setErrorMessage(t("collection.importCsvError"));
    }
  }, [file, t]);

  const handleClose = useCallback(() => {
    if (state === "success") {
      onSuccess();
    }
    // Reset state
    setState("idle");
    setFile(null);
    setStats(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClose();
  }, [state, onSuccess, onClose]);

  if (!isOpen) return null;

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
          </div>
        )}

        {/* File input (hidden in success state) */}
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
