import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useTriggerScan } from "../hooks/useScans";
import type { ScanRequest } from "../types/api";

const SCAN_TYPE_KEYS = [
  { value: "collection", labelKey: "scanForm.typeCollection" },
  { value: "set", labelKey: "scanForm.typeSet" },
  { value: "format", labelKey: "scanForm.typeFormat" },
  { value: "custom", labelKey: "scanForm.typeCustom" },
] as const;

interface ScanFormProps {
  onSuccess: () => void;
}

export function ScanForm({ onSuccess }: ScanFormProps) {
  const { t } = useTranslation();
  const [scanType, setScanType] = useState("collection");
  const [setCode, setSetCode] = useState("");
  const [formatName, setFormatName] = useState("");
  const [cardIdsText, setCardIdsText] = useState("");
  const [limit, setLimit] = useState("");
  const { trigger, loading, error } = useTriggerScan();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const body: ScanRequest = { scan_type: scanType };

    if (scanType === "set" && setCode.trim()) {
      body.set_codes = setCode
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
    if (scanType === "format" && formatName.trim()) {
      body.format_name = formatName.trim();
    }
    if (scanType === "custom" && cardIdsText.trim()) {
      body.card_ids = cardIdsText
        .split(",")
        .map((s) => parseInt(s.trim(), 10))
        .filter((n) => !isNaN(n));
    }
    if (limit.trim()) {
      const parsed = parseInt(limit.trim(), 10);
      if (!isNaN(parsed) && parsed > 0) {
        body.limit = parsed;
      }
    }

    try {
      await trigger(body);
      onSuccess();
    } catch {
      // error is set via the hook
    }
  };

  const inputClasses = "w-full rounded-tcg-md border border-tcg-border bg-tcg-card-alt px-3 py-2 text-sm text-white placeholder-tcg-dimmed focus:border-tcg-primary focus:outline-none focus:ring-1 focus:ring-tcg-primary transition-colors";

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-tcg-lg border border-tcg-border bg-tcg-card p-4 space-y-4"
      data-testid="scan-form"
    >
      {/* Scan type */}
      <div>
        <label
          htmlFor="scan-type"
          className="block text-sm font-medium text-tcg-muted mb-1"
        >
          {t("scanForm.scanType")}
        </label>
        <select
          id="scan-type"
          value={scanType}
          onChange={(e) => setScanType(e.target.value)}
          className={inputClasses}
          data-testid="scan-type-select"
        >
          {SCAN_TYPE_KEYS.map((st) => (
            <option key={st.value} value={st.value}>
              {t(st.labelKey)}
            </option>
          ))}
        </select>
      </div>

      {/* Conditional inputs */}
      {scanType === "set" && (
        <div>
          <label
            htmlFor="set-code"
            className="block text-sm font-medium text-tcg-muted mb-1"
          >
            {t("scanForm.setCodes")}
          </label>
          <input
            id="set-code"
            type="text"
            value={setCode}
            onChange={(e) => setSetCode(e.target.value)}
            placeholder={t("scanForm.setCodesPlaceholder")}
            className={inputClasses}
            data-testid="set-code-input"
          />
        </div>
      )}

      {scanType === "format" && (
        <div>
          <label
            htmlFor="format-name"
            className="block text-sm font-medium text-tcg-muted mb-1"
          >
            {t("scanForm.formatName")}
          </label>
          <input
            id="format-name"
            type="text"
            value={formatName}
            onChange={(e) => setFormatName(e.target.value)}
            placeholder={t("scanForm.formatNamePlaceholder")}
            className={inputClasses}
            data-testid="format-name-input"
          />
        </div>
      )}

      {scanType === "custom" && (
        <div>
          <label
            htmlFor="card-ids"
            className="block text-sm font-medium text-tcg-muted mb-1"
          >
            {t("scanForm.cardIds")}
          </label>
          <textarea
            id="card-ids"
            value={cardIdsText}
            onChange={(e) => setCardIdsText(e.target.value)}
            placeholder={t("scanForm.cardIdsPlaceholder")}
            rows={3}
            className={inputClasses}
            data-testid="card-ids-input"
          />
        </div>
      )}

      {/* Limit */}
      <div>
        <label
          htmlFor="scan-limit"
          className="block text-sm font-medium text-tcg-muted mb-1"
        >
          {t("scanForm.limitLabel")}
        </label>
        <input
          id="scan-limit"
          type="number"
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          placeholder={t("scanForm.limitPlaceholder")}
          min={1}
          className={inputClasses}
          data-testid="scan-limit-input"
        />
      </div>

      {error && (
        <p className="text-sm text-tcg-loss" data-testid="scan-form-error">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="rounded-tcg-md bg-tcg-primary px-4 py-2 text-sm font-medium text-white hover:bg-tcg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-tcg-glow"
        data-testid="scan-submit-button"
      >
        {loading ? t("scanForm.starting") : t("scanForm.startScan")}
      </button>
    </form>
  );
}
