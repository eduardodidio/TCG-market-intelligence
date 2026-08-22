import { useTranslation } from "react-i18next";

interface PeriodSelectorProps {
  value: string;
  onChange: (period: string) => void;
  periods?: string[];
  className?: string;
}

const DEFAULT_PERIODS = ["7d", "30d", "90d"];

export function PeriodSelector({
  value,
  onChange,
  periods = DEFAULT_PERIODS,
  className = "",
}: PeriodSelectorProps) {
  const { t } = useTranslation();

  return (
    <div
      className={`flex rounded-md overflow-hidden ${className}`}
      role="group"
      aria-label={t("market.periodSelector")}
    >
      {periods.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
            p === value
              ? "bg-indigo-500 text-white shadow-md"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
          }`}
        >
          {p}
        </button>
      ))}
    </div>
  );
}
