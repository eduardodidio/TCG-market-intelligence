import { useTranslation } from "react-i18next";
import type { GridSize } from "../utils/constants";

interface GridSizeToggleProps {
  value: GridSize;
  onChange: (size: GridSize) => void;
}

const SIZES: { key: GridSize; labelKey: string; icon: React.ReactNode }[] = [
  {
    key: "sm",
    labelKey: "gridSize.small",
    icon: (
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
        <rect x="1" y="1" width="4" height="4" rx="0.5" />
        <rect x="6" y="1" width="4" height="4" rx="0.5" />
        <rect x="11" y="1" width="4" height="4" rx="0.5" />
        <rect x="1" y="6" width="4" height="4" rx="0.5" />
        <rect x="6" y="6" width="4" height="4" rx="0.5" />
        <rect x="11" y="6" width="4" height="4" rx="0.5" />
        <rect x="1" y="11" width="4" height="4" rx="0.5" />
        <rect x="6" y="11" width="4" height="4" rx="0.5" />
        <rect x="11" y="11" width="4" height="4" rx="0.5" />
      </svg>
    ),
  },
  {
    key: "md",
    labelKey: "gridSize.medium",
    icon: (
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
        <rect x="1" y="1" width="6.5" height="6.5" rx="0.5" />
        <rect x="8.5" y="1" width="6.5" height="6.5" rx="0.5" />
        <rect x="1" y="8.5" width="6.5" height="6.5" rx="0.5" />
        <rect x="8.5" y="8.5" width="6.5" height="6.5" rx="0.5" />
      </svg>
    ),
  },
  {
    key: "lg",
    labelKey: "gridSize.large",
    icon: (
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
        <rect x="1" y="1" width="14" height="6.5" rx="0.5" />
        <rect x="1" y="8.5" width="14" height="6.5" rx="0.5" />
      </svg>
    ),
  },
];

export function GridSizeToggle({ value, onChange }: GridSizeToggleProps) {
  const { t } = useTranslation();
  return (
    <div className="flex" role="group" aria-label={t("gridSize.label")}>
      {SIZES.map((size, i) => (
        <button
          key={size.key}
          className={`px-2.5 py-2 transition-colors ${
            value === size.key
              ? "bg-slate-700 text-cyan-400 border border-cyan-400/50"
              : "bg-slate-800 text-slate-400 hover:text-white border border-slate-600"
          } ${i === 0 ? "rounded-l-md" : ""} ${i === SIZES.length - 1 ? "rounded-r-md" : ""}`}
          aria-label={t(size.labelKey)}
          aria-pressed={value === size.key}
          onClick={() => onChange(size.key)}
        >
          {size.icon}
        </button>
      ))}
    </div>
  );
}
