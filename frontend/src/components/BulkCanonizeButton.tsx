import { useState } from "react";
import { useTranslation } from "react-i18next";
import { canonizeAll } from "../api/collection";
import type { BulkCanonizeResult } from "../types/api";

export interface BulkCanonizeButtonProps {
  unlinkedCount: number;
  onComplete?: () => void;
}

export function BulkCanonizeButton({ unlinkedCount, onComplete }: BulkCanonizeButtonProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BulkCanonizeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (unlinkedCount <= 0 && !result && !error) {
    return null;
  }

  const handleClick = async () => {
    if (loading) return;
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await canonizeAll();
      if (res.errors.length > 0 || !res.data) {
        setError(res.errors[0]?.message || t("collection.canonizeError"));
      } else {
        setResult(res.data);
        onComplete?.();
      }
    } catch {
      setError(t("collection.canonizeError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="bulk-canonize-section">
      {/* Result banner */}
      {result && (
        <div
          data-testid="bulk-canonize-result"
          className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-emerald-900/50 border border-emerald-600/30 text-emerald-300 mb-2"
        >
          <svg className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <span>
            {t("collection.canonizeResult", { canonized: result.canonized, total: result.total })}
          </span>
          {result.failed > 0 && (
            <span className="text-amber-400">
              {t("collection.canonizeFailed", { failed: result.failed })}
            </span>
          )}
        </div>
      )}

      {/* Error banner */}
      {error && !result && (
        <div
          data-testid="bulk-canonize-error"
          className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-red-900/50 border border-red-600/30 text-red-300 mb-2"
        >
          <span>{error}</span>
        </div>
      )}

      {/* Button */}
      {unlinkedCount > 0 && !result && (
        <button
          type="button"
          onClick={handleClick}
          disabled={loading}
          data-testid="bulk-canonize-btn"
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
            bg-amber-600 hover:bg-amber-500 text-white rounded-lg
            transition-colors duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <svg
                className="h-4 w-4 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span>{t("collection.canonizing")}</span>
            </>
          ) : (
            <>
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                />
              </svg>
              <span>
                {t("collection.canonizeAll")} ({t("collection.unlinkedCount", { count: unlinkedCount })})
              </span>
            </>
          )}
        </button>
      )}
    </div>
  );
}
