import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { patchCollectionEntry } from "../api/collection";
import { formatCurrency, formatPercent } from "../utils/format";

interface PaidPriceQuickEditProps {
  entryId: number;
  acquisitionPrice: number | null;
  latestPrice: number | null;
  currency: string;
  compact?: boolean;
  onSaved: (entryId: number, price: number | null) => void;
}

const MAX_PRICE = 99999.99;

function stop(e: { preventDefault: () => void; stopPropagation: () => void }) {
  e.preventDefault();
  e.stopPropagation();
}

export function PaidPriceQuickEdit({
  entryId,
  acquisitionPrice,
  latestPrice,
  currency,
  compact = false,
  onSaved,
}: PaidPriceQuickEditProps) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(acquisitionPrice != null ? String(acquisitionPrice) : "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setDraft(acquisitionPrice != null ? String(acquisitionPrice) : "");
  }, [acquisitionPrice]);

  useEffect(() => {
    if (editing && inputRef.current) inputRef.current.focus();
  }, [editing]);

  const startEditing = (e: React.MouseEvent) => {
    stop(e);
    setError(null);
    setEditing(true);
  };

  const cancelEditing = (e?: React.MouseEvent) => {
    if (e) stop(e);
    setDraft(acquisitionPrice != null ? String(acquisitionPrice) : "");
    setEditing(false);
    setError(null);
  };

  const handleSave = async (e?: React.MouseEvent) => {
    if (e) stop(e);
    const trimmed = draft.trim();
    const numVal = trimmed ? parseFloat(trimmed.replace(",", ".")) : null;
    if (numVal !== null && (isNaN(numVal) || numVal <= 0 || numVal > MAX_PRICE)) {
      setError(t("portfolio.invalidPrice"));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await patchCollectionEntry(entryId, { acquisition_price: numVal });
      if (res.data) {
        setEditing(false);
        onSaved(entryId, numVal);
      } else {
        setError(t("inlineEdit.saveError"));
      }
    } catch {
      setError(t("inlineEdit.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    stop(e);
    if (e.key === "Enter") {
      handleSave();
    } else if (e.key === "Escape") {
      cancelEditing();
    }
  };

  const pnlPct =
    acquisitionPrice != null && acquisitionPrice > 0 && latestPrice != null && currency === "BRL"
      ? ((latestPrice - acquisitionPrice) / acquisitionPrice) * 100
      : null;

  const editTitle =
    acquisitionPrice != null
      ? `${t("collection.paidPrice")}: ${formatCurrency(acquisitionPrice, "BRL")}`
      : t("collection.setPaidPrice");

  return (
    <div
      data-testid={`paid-price-quick-edit-${entryId}`}
      onClick={stop}
      onMouseDown={stop}
      className="flex items-center gap-1.5"
    >
      {!editing ? (
        <div className="flex items-center gap-1.5" data-testid="paid-price-display">
          {compact ? (
            <button
              onClick={startEditing}
              data-testid="paid-price-edit-btn"
              title={editTitle}
              className="text-slate-400 hover:text-cyan-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                />
              </svg>
            </button>
          ) : acquisitionPrice != null ? (
            <>
              <span className="text-xs text-slate-400">
                {t("collection.paidPrice")}: {formatCurrency(acquisitionPrice, "BRL")}
              </span>
              <button
                onClick={startEditing}
                data-testid="paid-price-edit-btn"
                title={t("inlineEdit.edit")}
                className="text-slate-400 hover:text-cyan-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
              >
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                  />
                </svg>
              </button>
            </>
          ) : (
            <button
              onClick={startEditing}
              data-testid="paid-price-edit-btn"
              title={t("collection.setPaidPrice")}
              className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
            >
              {t("collection.setPaidPrice")}
            </button>
          )}
          {pnlPct != null && (
            <span
              data-testid="paid-price-pnl"
              className={pnlPct >= 0 ? "text-xs text-emerald-400" : "text-xs text-red-400"}
            >
              {formatPercent(pnlPct)}
            </span>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-1.5">
          <input
            ref={inputRef}
            type="text"
            inputMode="decimal"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onClick={stop}
            disabled={saving}
            placeholder="0.00"
            data-testid="paid-price-field"
            className="rounded-md bg-slate-700 border border-slate-600 px-2 py-1 text-xs text-white w-20 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
          />
          <button
            onClick={handleSave}
            disabled={saving}
            data-testid="paid-price-save"
            className="text-green-400 hover:text-green-300 disabled:opacity-50 transition-colors"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </button>
          <button
            onClick={cancelEditing}
            disabled={saving}
            data-testid="paid-price-cancel"
            className="text-slate-400 hover:text-red-400 disabled:opacity-50 transition-colors"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
      {error && (
        <p className="text-xs text-red-400" data-testid="paid-price-error">
          {error}
        </p>
      )}
    </div>
  );
}
