interface FilterOption {
  label: string;
  value: string;
  icon?: string;
}

interface FilterChipsProps {
  options: FilterOption[];
  selected: string | null;
  onSelect: (value: string | null) => void;
}

export function FilterChips({ options, selected, onSelect }: FilterChipsProps) {
  return (
    <div
      className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin"
      data-testid="filter-chips"
    >
      <button
        onClick={() => onSelect(null)}
        className={`shrink-0 px-3 py-1 rounded-full text-sm font-medium transition-colors ${
          selected === null
            ? "bg-indigo-500 text-white shadow-md"
            : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
        }`}
        data-testid="filter-chip-all"
      >
        All
      </button>
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() =>
            onSelect(option.value === selected ? null : option.value)
          }
          className={`shrink-0 px-3 py-1 rounded-full text-sm font-medium transition-colors flex items-center ${
            selected === option.value
              ? "bg-indigo-500 text-white shadow-md"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
          }`}
          data-testid={`filter-chip-${option.value}`}
        >
          {option.icon && (
            <img
              src={option.icon}
              className="w-4 h-4 invert brightness-200 inline mr-1"
              onError={(e) => { e.currentTarget.style.display = "none"; }}
              alt=""
              data-testid={`filter-chip-icon-${option.value}`}
            />
          )}
          {option.label}
        </button>
      ))}
    </div>
  );
}
