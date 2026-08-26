import { useTranslation } from "react-i18next";

export interface MaxAgeDaysSelectProps {
  value: number | undefined;
  onChange: (value: number | undefined) => void;
  disabled?: boolean;
}

const OPTIONS: { labelKey: string; value: number | undefined }[] = [
  { labelKey: "collection.maxAgeDaysOption1", value: 1 },
  { labelKey: "collection.maxAgeDaysOption3", value: 3 },
  { labelKey: "collection.maxAgeDaysOption7", value: 7 },
  { labelKey: "collection.maxAgeDaysOptionAll", value: undefined },
];

export function MaxAgeDaysSelect({
  value,
  onChange,
  disabled = false,
}: MaxAgeDaysSelectProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center gap-1" data-testid="max-age-days-select">
      <label className="text-xs text-slate-400">
        {t("collection.maxAgeDays")}
      </label>
      <select
        data-testid="max-age-days-dropdown"
        value={value ?? "all"}
        onChange={(e) => {
          const v = e.target.value;
          onChange(v === "all" ? undefined : Number(v));
        }}
        disabled={disabled}
        className="bg-slate-700 border border-slate-600 text-slate-200 text-sm rounded-lg
          px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-cyan-400
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {OPTIONS.map((opt) => (
          <option key={opt.value ?? "all"} value={opt.value ?? "all"}>
            {t(opt.labelKey)}
          </option>
        ))}
      </select>
    </div>
  );
}
