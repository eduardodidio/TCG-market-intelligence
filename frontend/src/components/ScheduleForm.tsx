import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { ScheduleCreateRequest, ScheduleResponse } from "../types/api";

const CRON_PRESETS = [
  { label: "schedules.presets.daily6am", cron: "0 6 * * *" },
  { label: "schedules.presets.every12h", cron: "0 */12 * * *" },
  { label: "schedules.presets.weeklyMon", cron: "0 3 * * 1" },
  { label: "schedules.presets.monthly", cron: "0 0 1 * *" },
] as const;

interface ScheduleFormProps {
  initial?: ScheduleResponse | null;
  onSubmit: (data: ScheduleCreateRequest) => void;
  onCancel: () => void;
  submitting?: boolean;
}

export function ScheduleForm({
  initial,
  onSubmit,
  onCancel,
  submitting = false,
}: ScheduleFormProps) {
  const { t } = useTranslation();

  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [cronExpression, setCronExpression] = useState(
    initial?.cron_expression ?? "0 6 * * *",
  );
  const [scanType, setScanType] = useState(initial?.scan_type ?? "collection");
  const [filtersJson, setFiltersJson] = useState(
    initial?.filters_json ?? "{}",
  );
  const [maxRetries, setMaxRetries] = useState(initial?.max_retries ?? 3);
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !cronExpression.trim()) {
      setError(t("deckImport.requiredError"));
      return;
    }
    setError("");
    onSubmit({
      name: name.trim(),
      cron_expression: cronExpression.trim(),
      scan_type: scanType,
      filters_json: filtersJson,
      description: description.trim() || undefined,
      max_retries: maxRetries,
    });
  }

  return (
    <div
      className="bg-slate-800 border border-slate-600 rounded-lg p-6"
      data-testid="schedule-form"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {t("schedules.name")}
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-400"
            placeholder="e.g. Daily Collection Scan"
            data-testid="schedule-name-input"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {t("schedules.description")}
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-400"
            placeholder={t("schedules.description")}
            data-testid="schedule-desc-input"
          />
        </div>

        {/* Cron Expression */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {t("schedules.cron")}
          </label>
          <input
            type="text"
            value={cronExpression}
            onChange={(e) => setCronExpression(e.target.value)}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-400"
            placeholder="0 6 * * *"
            data-testid="schedule-cron-input"
          />
          <p className="mt-1 text-xs text-slate-400">{t("schedules.cronHelp")}</p>

          {/* Presets */}
          <div className="flex flex-wrap gap-2 mt-2" data-testid="cron-presets">
            {CRON_PRESETS.map((preset) => (
              <button
                key={preset.cron}
                type="button"
                onClick={() => setCronExpression(preset.cron)}
                className={`px-2 py-1 text-xs rounded border transition-colors ${
                  cronExpression === preset.cron
                    ? "bg-cyan-600 border-cyan-500 text-white"
                    : "bg-slate-700 border-slate-600 text-slate-300 hover:border-cyan-400"
                }`}
                data-testid={`preset-${preset.cron.replace(/[* /]/g, "_")}`}
              >
                {t(preset.label)}
              </button>
            ))}
          </div>
        </div>

        {/* Scan Type */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {t("schedules.scanType")}
          </label>
          <select
            value={scanType}
            onChange={(e) => setScanType(e.target.value)}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
            data-testid="schedule-type-select"
          >
            <option value="collection">{t("scanForm.typeCollection")}</option>
            <option value="set">{t("scanForm.typeSet")}</option>
            <option value="format">{t("scanForm.typeFormat")}</option>
            <option value="custom">{t("scanForm.typeCustom")}</option>
          </select>
        </div>

        {/* Max Retries */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            {t("schedules.maxRetries")}
          </label>
          <input
            type="number"
            value={maxRetries}
            onChange={(e) => setMaxRetries(parseInt(e.target.value, 10) || 3)}
            min={1}
            max={10}
            className="w-24 px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
            data-testid="schedule-retries-input"
          />
        </div>

        {/* Filters JSON */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Filters (JSON)
          </label>
          <textarea
            value={filtersJson}
            onChange={(e) => setFiltersJson(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-400 font-mono text-sm"
            data-testid="schedule-filters-input"
          />
        </div>

        {error && (
          <p className="text-red-400 text-sm" data-testid="schedule-form-error">
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium disabled:opacity-50 transition-colors"
            data-testid="schedule-submit-btn"
          >
            {submitting
              ? t("common.pleaseWait")
              : initial
                ? t("schedules.edit")
                : t("schedules.new")}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded font-medium transition-colors"
            data-testid="schedule-cancel-btn"
          >
            {t("common.cancel")}
          </button>
        </div>
      </form>
    </div>
  );
}
