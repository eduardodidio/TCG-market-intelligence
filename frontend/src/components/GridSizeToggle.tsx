import type { GridSize } from "../utils/constants";

interface GridSizeToggleProps {
  value: GridSize;
  onChange: (size: GridSize) => void;
}

const SIZES: { key: GridSize; label: string; icon: React.ReactNode }[] = [
  {
    key: "sm",
    label: "Small grid",
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
    label: "Medium grid",
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
    label: "Large grid",
    icon: (
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
        <rect x="1" y="1" width="14" height="6.5" rx="0.5" />
        <rect x="1" y="8.5" width="14" height="6.5" rx="0.5" />
      </svg>
    ),
  },
];

export function GridSizeToggle({ value, onChange }: GridSizeToggleProps) {
  return (
    <div className="flex" role="group" aria-label="Grid size">
      {SIZES.map((size, i) => (
        <button
          key={size.key}
          className={`px-2.5 py-2 transition-colors ${
            value === size.key
              ? "bg-slate-600 text-cyan-400 border border-cyan-500/50"
              : "bg-slate-800 text-slate-400 hover:text-white border border-slate-700"
          } ${i === 0 ? "rounded-l-lg" : ""} ${i === SIZES.length - 1 ? "rounded-r-lg" : ""}`}
          aria-label={size.label}
          aria-pressed={value === size.key}
          onClick={() => onChange(size.key)}
        >
          {size.icon}
        </button>
      ))}
    </div>
  );
}
