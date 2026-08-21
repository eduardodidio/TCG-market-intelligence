import { useEffect, useState } from "react";
import { ScanForm } from "../components/ScanForm";
import { ScanHistoryTable } from "../components/ScanHistoryTable";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { useScans } from "../hooks/useScans";

export function Scans() {
  useEffect(() => {
    document.title = "Price Scans | TCG Market";
  }, []);

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
        <h2 className="text-2xl font-bold text-white">Price Scans</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
          data-testid="new-scan-toggle"
        >
          {showForm ? "Cancel" : "New Scan"}
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
      {loading && <LoadingSpinner message="Loading scans..." />}

      {/* Scan history table */}
      {!loading && <ScanHistoryTable scans={scans} />}
    </div>
  );
}
