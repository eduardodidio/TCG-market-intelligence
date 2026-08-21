export interface SortOption {
  label: string;
  sortBy: string;
  sortDir: "asc" | "desc";
}

export interface SortSelectProps {
  options: SortOption[];
  value: string;
  onChange: (sortBy: string, sortDir: "asc" | "desc") => void;
}

export const COLLECTION_SORT_OPTIONS: SortOption[] = [
  { label: "Name (A-Z)", sortBy: "name", sortDir: "asc" },
  { label: "Name (Z-A)", sortBy: "name", sortDir: "desc" },
  { label: "Set", sortBy: "set", sortDir: "asc" },
  { label: "Card Number", sortBy: "number", sortDir: "asc" },
  { label: "Date Added (Newest)", sortBy: "added", sortDir: "desc" },
  { label: "Date Added (Oldest)", sortBy: "added", sortDir: "asc" },
  { label: "Price (High-Low)", sortBy: "price", sortDir: "desc" },
  { label: "Price (Low-High)", sortBy: "price", sortDir: "asc" },
];

export function SortSelect({ options, value, onChange }: SortSelectProps) {
  return (
    <select
      data-testid="sort-select"
      value={value}
      onChange={(e) => {
        const [sortBy, sortDir] = e.target.value.split("-");
        onChange(sortBy, sortDir as "asc" | "desc");
      }}
      className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg
        text-white text-sm
        focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent
        cursor-pointer"
    >
      {options.map((opt) => {
        const key = `${opt.sortBy}-${opt.sortDir}`;
        return (
          <option key={key} value={key}>
            {opt.label}
          </option>
        );
      })}
    </select>
  );
}
