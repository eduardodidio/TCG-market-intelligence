import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { patchCollectionEntry } from "../api/collection";
import { formatCurrency } from "../utils/format";

interface AcquisitionPriceInputProps {
  entryId: number;
  acquisitionPrice: number | null;
  acquiredAt: string | null;
  currency?: string;
  onSaved?: (price: number | null, acquiredAt: string | null) => void;
}

/**
 * Inline editable fields for acquisition price and acquired date.
 * Saves via PATCH /collection/{id}.
 */
export function AcquisitionPriceInput({
  entryId,
  acquisitionPrice,
  acquiredAt,
  currency = "BRL",
  onSaved,
}: AcquisitionPriceInputProps) {
  const { t } = useTranslation();
  const [editingPrice, setEditingPrice] = useState(false);
  const [editingDate, setEditingDate] = useState(false);
  const [priceDraft, setPriceDraft] = useState(acquisitionPrice != null ? String(acquisitionPrice) : "");
  const [dateDraft, setDateDraft] = useState(acquiredAt || "");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const priceInputRef = useRef<HTMLInputElement>(null);
  const dateInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setPriceDraft(acquisitionPrice != null ? String(acquisitionPrice) : "");
  }, [acquisitionPrice]);

  useEffect(() => {
    setDateDraft(acquiredAt || "");
  }, [acquiredAt]);

  useEffect(() => {
    if (editingPrice && priceInputRef.current) priceInputRef.current.focus();
  }, [editingPrice]);

  useEffect(() => {
    if (editingDate && dateInputRef.current) dateInputRef.current.focus();
  }, [editingDate]);

  const handleSavePrice = async () => {
    const numVal = priceDraft ? parseFloat(priceDraft) : null;
    if (numVal !== null && (isNaN(numVal) || numVal <= 0)) {
      setError(t("portfolio.invalidPrice"));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updates: Record<string, unknown> = {};
      if (numVal !== null) {
        updates.acquisition_price = numVal;
      }
      const res = await patchCollectionEntry(entryId, updates as { acquisition_price?: number });
      if (res.data) {
        setEditingPrice(false);
        setSuccess(true);
        setTimeout(() => setSuccess(false), 1500);
        onSaved?.(numVal, acquiredAt);
      } else {
        setError(t("inlineEdit.saveError"));
      }
    } catch {
      setError(t("inlineEdit.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const handleSaveDate = async () => {
    setSaving(true);
    setError(null);
    try {
      const updates: Record<string, unknown> = {};
      if (dateDraft) {
        updates.acquired_at = dateDraft;
      }
      const res = await patchCollectionEntry(entryId, updates as { acquired_at?: string });
      if (res.data) {
        setEditingDate(false);
        setSuccess(true);
        setTimeout(() => setSuccess(false), 1500);
        onSaved?.(acquisitionPrice, dateDraft || null);
      } else {
        setError(t("inlineEdit.saveError"));
      }
    } catch {
      setError(t("inlineEdit.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const handlePriceKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSavePrice();
    } else if (e.key === "Escape") {
      setPriceDraft(acquisitionPrice != null ? String(acquisitionPrice) : "");
      setEditingPrice(false);
      setError(null);
    }
  };

  const handleDateKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSaveDate();
    } else if (e.key === "Escape") {
      setDateDraft(acquiredAt || "");
      setEditingDate(false);
      setError(null);
    }
  };

  return (
    <div className="space-y-3" data-testid="acquisition-price-input">
      {/* Acquisition Price */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500 uppercase tracking-wider">
          {t("portfolio.acquisitionPrice")}
        </span>
        {!editingPrice ? (
          <div className="flex items-center gap-2" data-testid="acquisition-price-display">
            <span className="text-sm text-slate-300">
              {acquisitionPrice != null
                ? formatCurrency(acquisitionPrice, currency)
                : t("inlineEdit.empty")}
            </span>
            {success && (
              <svg
                className="h-4 w-4 text-emerald-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            )}
            <button
              onClick={() => setEditingPrice(true)}
              title={t("inlineEdit.edit")}
              data-testid="acquisition-price-edit-btn"
              className="text-slate-400 hover:text-cyan-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              ref={priceInputRef}
              type="number"
              step="0.01"
              min="0.01"
              value={priceDraft}
              onChange={(e) => setPriceDraft(e.target.value)}
              onKeyDown={handlePriceKeyDown}
              disabled={saving}
              placeholder="0.00"
              data-testid="acquisition-price-field"
              className="rounded-md bg-slate-700 border border-slate-600 px-2 py-1 text-sm text-white w-28 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
            />
            <button
              onClick={handleSavePrice}
              disabled={saving}
              data-testid="acquisition-price-save"
              className="text-green-400 hover:text-green-300 disabled:opacity-50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </button>
            <button
              onClick={() => {
                setPriceDraft(acquisitionPrice != null ? String(acquisitionPrice) : "");
                setEditingPrice(false);
                setError(null);
              }}
              disabled={saving}
              className="text-slate-400 hover:text-red-400 disabled:opacity-50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Acquired At */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500 uppercase tracking-wider">
          {t("portfolio.acquiredAt")}
        </span>
        {!editingDate ? (
          <div className="flex items-center gap-2" data-testid="acquired-at-display">
            <span className="text-sm text-slate-300">
              {acquiredAt || t("inlineEdit.empty")}
            </span>
            <button
              onClick={() => setEditingDate(true)}
              title={t("inlineEdit.edit")}
              data-testid="acquired-at-edit-btn"
              className="text-slate-400 hover:text-cyan-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              ref={dateInputRef}
              type="date"
              value={dateDraft}
              onChange={(e) => setDateDraft(e.target.value)}
              onKeyDown={handleDateKeyDown}
              disabled={saving}
              data-testid="acquired-at-field"
              className="rounded-md bg-slate-700 border border-slate-600 px-2 py-1 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
            />
            <button
              onClick={handleSaveDate}
              disabled={saving}
              data-testid="acquired-at-save"
              className="text-green-400 hover:text-green-300 disabled:opacity-50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </button>
            <button
              onClick={() => {
                setDateDraft(acquiredAt || "");
                setEditingDate(false);
                setError(null);
              }}
              disabled={saving}
              className="text-slate-400 hover:text-red-400 disabled:opacity-50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-400" data-testid="acquisition-error">{error}</p>
      )}
    </div>
  );
}
