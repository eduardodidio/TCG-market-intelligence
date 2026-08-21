import { useTranslation } from "react-i18next";

export interface SortOption {
  labelKey: string;
  sortBy: string;
  sortDir: "asc" | "desc";
}

export interface SortSelectProps {
  options: SortOption[];
  value: string;
  onChange: (sortBy: string, sortDir: "asc" | "desc") => void;
}

export const COLLECTION_SORT_OPTIONS: SortOption[] = [
  { labelKey: "sort.nameAZ", sortBy: "name", sortDir: "asc" },
  { labelKey: "sort.nameZA", sortBy: "name", sortDir: "desc" },
  { labelKey: "sort.set", sortBy: "set", sortDir: "asc" },
  { labelKey: "sort.cardNumber", sortBy: "number", sortDir: "asc" },
  { labelKey: "sort.dateNewest", sortBy: "added", sortDir: "desc" },
  { labelKey: "sort.dateOldest", sortBy: "added", sortDir: "asc" },
  { labelKey: "sort.priceHighLow", sortBy: "price", sortDir: "desc" },
  { labelKey: "sort.priceLowHigh", sortBy: "price", sortDir: "asc" },
];

export function SortSelect({ options, value, onChange }: SortSelectProps) {
  const { t } = useTranslation();
  return (
    <select
      data-testid="sort-select"
      value={value}
      onChange={(e) => {
        const [sortBy, sortDir] = e.target.value.split("-");
        onChange(sortBy, sortDir as "asc" | "desc");
      }}
      className="px-3 py-2 bg-slate-800 border border-slate-600 rounded-md
        text-white text-sm
        focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
        cursor-pointer transition-colors"
    >
      {options.map((opt) => {
        const key = `${opt.sortBy}-${opt.sortDir}`;
        return (
          <option key={key} value={key}>
            {t(opt.labelKey)}
          </option>
        );
      })}
    </select>
  );
}
