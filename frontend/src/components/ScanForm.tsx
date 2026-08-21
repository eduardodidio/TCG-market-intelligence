import { useState } from "react";
import { useTriggerScan } from "../hooks/useScans";
import type { ScanRequest } from "../types/api";

const SCAN_TYPES = [
  { value: "collection", label: "Collection" },
  { value: "set", label: "By Set" },
  { value: "format", label: "By Format" },
  { value: "custom", label: "Custom" },
] as const;

interface ScanFormProps {
  onSuccess: () => void;
}

export function ScanForm({ onSuccess }: ScanFormProps) {
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

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-4"
      data-testid="scan-form"
    >
      {/* Scan type */}
      <div>
        <label
          htmlFor="scan-type"
          className="block text-sm font-medium text-slate-300 mb-1"
        >
          Scan Type
        </label>
        <select
          id="scan-type"
          value={scanType}
          onChange={(e) => setScanType(e.target.value)}
          className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
          data-testid="scan-type-select"
        >
          {SCAN_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {/* Conditional inputs */}
      {scanType === "set" && (
        <div>
          <label
            htmlFor="set-code"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Set Code(s)
          </label>
          <input
            id="set-code"
            type="text"
            value={setCode}
            onChange={(e) => setSetCode(e.target.value)}
            placeholder="e.g. DMR, MH2"
            className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white placeholder-slate-400 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
            data-testid="set-code-input"
          />
        </div>
      )}

      {scanType === "format" && (
        <div>
          <label
            htmlFor="format-name"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Format Name
          </label>
          <input
            id="format-name"
            type="text"
            value={formatName}
            onChange={(e) => setFormatName(e.target.value)}
            placeholder="e.g. modern, standard"
            className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white placeholder-slate-400 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
            data-testid="format-name-input"
          />
        </div>
      )}

      {scanType === "custom" && (
        <div>
          <label
            htmlFor="card-ids"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Card IDs
          </label>
          <textarea
            id="card-ids"
            value={cardIdsText}
            onChange={(e) => setCardIdsText(e.target.value)}
            placeholder="Comma-separated IDs, e.g. 1, 42, 99"
            rows={3}
            className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white placeholder-slate-400 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
            data-testid="card-ids-input"
          />
        </div>
      )}

      {/* Limit */}
      <div>
        <label
          htmlFor="scan-limit"
          className="block text-sm font-medium text-slate-300 mb-1"
        >
          Limit (optional)
        </label>
        <input
          id="scan-limit"
          type="number"
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          placeholder="Max cards to scan"
          min={1}
          className="w-full rounded-md border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-white placeholder-slate-400 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400"
          data-testid="scan-limit-input"
        />
      </div>

      {error && (
        <p className="text-sm text-red-400" data-testid="scan-form-error">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        data-testid="scan-submit-button"
      >
        {loading ? "Starting..." : "Start Scan"}
      </button>
    </form>
  );
}
