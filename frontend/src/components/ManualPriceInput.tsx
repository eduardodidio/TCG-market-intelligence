import { useState } from "react";
import { useTranslation } from "react-i18next";
import { setManualPrice } from "../api/collection";
import { CurrencyIndicator } from "./CurrencyIndicator";

interface ManualPriceInputProps {
  entryId: number;
  currency: string;
  onSaved: () => void;
}

/**
 * Numeric input for manually setting a card's price.
 * Validates: price > 0, max 99999.99.
 * On success, calls onSaved callback and shows brief success state.
 */
export function ManualPriceInput({ entryId, currency, onSaved }: ManualPriceInputProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSave = async () => {
    setError(null);
    setSuccess(false);

    const price = parseFloat(value);
    if (isNaN(price) || price <= 0 || price > 99999.99) {
      setError(t("price.invalidPrice"));
      return;
    }

    setSaving(true);
    try {
      const res = await setManualPrice(entryId, price, currency);
      if (res.data) {
        setSuccess(true);
        setValue("");
        onSaved();
        setTimeout(() => setSuccess(false), 3000);
      } else {
        const msg = res.errors?.[0]?.message || t("common.unknownError");
        setError(msg);
      }
    } catch {
      setError(t("common.unknownError"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-testid="manual-price-input" className="mt-4">
      <p className="text-sm text-slate-400 mb-2">{t("price.setPrice")}</p>
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 flex items-center pl-2.5 pointer-events-none">
            <CurrencyIndicator currency={currency} size={16} />
          </div>
          <input
            data-testid="manual-price-field"
            type="number"
            step="0.01"
            min="0.01"
            max="99999.99"
            placeholder={t("price.enterPrice")}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setError(null);
              setSuccess(false);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSave();
            }}
            className="w-full rounded-md bg-slate-700 border border-slate-600 pl-9 pr-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
          />
        </div>
        <button
          data-testid="manual-price-save"
          onClick={handleSave}
          disabled={saving || !value}
          className="rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {saving ? t("common.pleaseWait") : t("price.save")}
        </button>
      </div>
      {error && (
        <p data-testid="manual-price-error" className="text-xs text-red-400 mt-1">
          {error}
        </p>
      )}
      {success && (
        <p data-testid="manual-price-success" className="text-xs text-green-400 mt-1">
          {t("price.saved")}
        </p>
      )}
    </div>
  );
}
