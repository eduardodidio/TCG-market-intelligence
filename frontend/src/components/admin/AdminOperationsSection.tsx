import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  triggerLigaScan,
  triggerCatalogScan,
  downloadBackup,
} from "../../api/admin";

function OperationsContent() {
  const { t } = useTranslation();

  // Liga scan state
  const [maxAgeDays, setMaxAgeDays] = useState("1");
  const [ligaLoading, setLigaLoading] = useState(false);
  const [ligaResult, setLigaResult] = useState<{ scan_id: number } | null>(null);
  const [ligaError, setLigaError] = useState<string | null>(null);

  // Catalog scan state
  const [setCode, setSetCode] = useState("");
  const [delay, setDelay] = useState("2.0");
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogResult, setCatalogResult] = useState<{ scan_id: number } | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  // Backup state
  const [backupLoading, setBackupLoading] = useState(false);

  const handleLigaScan = useCallback(async () => {
    setLigaLoading(true);
    setLigaError(null);
    setLigaResult(null);
    const resp = await triggerLigaScan(parseInt(maxAgeDays, 10) || 1);
    setLigaLoading(false);
    if (resp.errors.length > 0) {
      setLigaError(resp.errors.map((e) => e.message).join("; "));
    } else if (resp.data) {
      setLigaResult({ scan_id: resp.data.scan_id });
    }
  }, [maxAgeDays]);

  const handleCatalogScan = useCallback(async () => {
    if (!setCode.trim()) return;
    setCatalogLoading(true);
    setCatalogError(null);
    setCatalogResult(null);
    const resp = await triggerCatalogScan(setCode.trim(), parseFloat(delay) || 2.0);
    setCatalogLoading(false);
    if (resp.errors.length > 0) {
      setCatalogError(resp.errors.map((e) => e.message).join("; "));
    } else if (resp.data) {
      setCatalogResult({ scan_id: resp.data.scan_id });
    }
  }, [setCode, delay]);

  const handleBackup = useCallback(() => {
    setBackupLoading(true);
    downloadBackup();
    // Reset after a short delay since we can't track download progress
    setTimeout(() => setBackupLoading(false), 2000);
  }, []);

  return (
    <div data-testid="operations-section" className="space-y-6">
      {/* Liga Scan */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 className="text-white font-medium mb-3" data-testid="liga-scan-title">
          {t("admin.ops.ligaScan")}
        </h3>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              {t("admin.ops.maxAgeDays")}
            </label>
            <input
              type="number"
              value={maxAgeDays}
              onChange={(e) => setMaxAgeDays(e.target.value)}
              min={1}
              className="w-20 px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
              data-testid="liga-max-age-input"
            />
          </div>
          <button
            onClick={handleLigaScan}
            disabled={ligaLoading}
            className="px-4 py-2 text-sm bg-indigo-700 hover:bg-indigo-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded"
            data-testid="run-liga-scan-btn"
          >
            {ligaLoading ? t("common.pleaseWait") : t("admin.ops.runLigaScan")}
          </button>
        </div>
        {ligaResult && (
          <p className="mt-2 text-sm text-green-400" data-testid="liga-scan-result">
            {t("admin.ops.jobStarted")} - {t("admin.ops.scanId")}: {ligaResult.scan_id}
          </p>
        )}
        {ligaError && (
          <p className="mt-2 text-sm text-red-400" data-testid="liga-scan-error">
            {ligaError}
          </p>
        )}
      </div>

      {/* Catalog Sweep */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 className="text-white font-medium mb-3" data-testid="catalog-sweep-title">
          {t("admin.ops.catalogSweep")}
        </h3>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              {t("admin.ops.setCode")}
            </label>
            <input
              type="text"
              value={setCode}
              onChange={(e) => setSetCode(e.target.value)}
              placeholder="mh3"
              className="w-24 px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
              data-testid="catalog-set-code-input"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              {t("admin.ops.delay")}
            </label>
            <input
              type="number"
              value={delay}
              onChange={(e) => setDelay(e.target.value)}
              step={0.5}
              min={0.5}
              max={10}
              className="w-20 px-3 py-2 text-sm bg-slate-900 border border-slate-600 text-white rounded focus:outline-none focus:border-cyan-400"
              data-testid="catalog-delay-input"
            />
          </div>
          <button
            onClick={handleCatalogScan}
            disabled={catalogLoading || !setCode.trim()}
            className="px-4 py-2 text-sm bg-indigo-700 hover:bg-indigo-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded"
            data-testid="sweep-set-btn"
          >
            {catalogLoading ? t("common.pleaseWait") : t("admin.ops.sweepSet")}
          </button>
        </div>
        {catalogResult && (
          <p className="mt-2 text-sm text-green-400" data-testid="catalog-scan-result">
            {t("admin.ops.jobStarted")} - {t("admin.ops.scanId")}: {catalogResult.scan_id}
          </p>
        )}
        {catalogError && (
          <p className="mt-2 text-sm text-red-400" data-testid="catalog-scan-error">
            {catalogError}
          </p>
        )}
      </div>

      {/* DB Backup */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 className="text-white font-medium mb-3" data-testid="db-backup-title">
          {t("admin.ops.dbBackup")}
        </h3>
        <button
          onClick={handleBackup}
          disabled={backupLoading}
          className="px-4 py-2 text-sm bg-green-700 hover:bg-green-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded"
          data-testid="download-backup-btn"
        >
          {backupLoading ? t("common.pleaseWait") : t("admin.ops.downloadBackup")}
        </button>
      </div>
    </div>
  );
}

export function AdminOperationsSection({ isOpen }: { isOpen: boolean }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (isOpen && !loaded) {
      setLoaded(true);
    }
  }, [isOpen, loaded]);

  if (!loaded) return null;

  return <OperationsContent />;
}
