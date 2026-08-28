import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ScanForm } from "../ScanForm";
import { ScanHistoryTable } from "../ScanHistoryTable";
import { ErrorBanner } from "../ErrorBanner";
import { LoadingSpinner } from "../LoadingSpinner";
import { useScans } from "../../hooks/useScans";

function ScansContent() {
  const { t } = useTranslation();
  const [showForm, setShowForm] = useState(false);
  const { scans, loading, error, refetch } = useScans({ limit: 50 });

  const handleScanSuccess = () => {
    setShowForm(false);
    refetch();
  };

  return (
    <div data-testid="scans-section">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-white">{t("scans.title")}</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors shadow-md"
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

export function AdminScansSection({ isOpen }: { isOpen: boolean }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (isOpen && !loaded) {
      setLoaded(true);
    }
  }, [isOpen, loaded]);

  if (!loaded) return null;

  return <ScansContent />;
}
