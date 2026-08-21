import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ScanForm } from "../components/ScanForm";
import { ScanHistoryTable } from "../components/ScanHistoryTable";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { useScans } from "../hooks/useScans";

export function Scans() {
  const { t } = useTranslation();

  useEffect(() => {
    document.title = `${t("scans.title")} | TCG Market`;
  }, [t]);

  const [showForm, setShowForm] = useState(false);
  const { scans, loading, error, refetch } = useScans({ limit: 50 });

  const handleScanSuccess = () => {
    setShowForm(false);
    refetch();
  };

  return (
    <div data-testid="page-scans">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">{t("scans.title")}</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-tcg-md bg-tcg-primary px-4 py-2 text-sm font-medium text-white hover:bg-tcg-primary-hover transition-colors shadow-tcg-glow"
          data-testid="new-scan-toggle"
        >
          {showForm ? t("common.cancel") : t("scans.newScan")}
        </button>
      </div>

      {/* Collapsible form */}
      {showForm && (
        <div className="mb-6" data-testid="scan-form-container">
          <ScanForm onSuccess={handleScanSuccess} />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mb-6">
          <ErrorBanner message={error} variant="inline" />
        </div>
      )}

      {/* Loading state */}
      {loading && <LoadingSpinner message={t("scans.loadingScans")} />}

      {/* Scan history table */}
      {!loading && <ScanHistoryTable scans={scans} />}
    </div>
  );
}
