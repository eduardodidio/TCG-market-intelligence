import type { SortOption } from "../components/SortSelect";

export const MARKETPLACE_SORT_OPTIONS: SortOption[] = [
  { labelKey: "sort.nameAZ", sortBy: "name", sortDir: "asc" },
  { labelKey: "sort.nameZA", sortBy: "name", sortDir: "desc" },
  { labelKey: "sort.set", sortBy: "set", sortDir: "asc" },
  { labelKey: "sort.cardNumber", sortBy: "number", sortDir: "asc" },
  { labelKey: "sort.priceHighLow", sortBy: "price", sortDir: "desc" },
  { labelKey: "sort.priceLowHigh", sortBy: "price", sortDir: "asc" },
];

export const DUPLICATES_SORT_OPTIONS: SortOption[] = [
  { labelKey: "tradeFilters.sortQuantityDesc", sortBy: "quantity", sortDir: "desc" },
  ...MARKETPLACE_SORT_OPTIONS,
];

export const MY_TRADES_SORT_OPTIONS: SortOption[] = [
  { labelKey: "tradeFilters.sortNewest", sortBy: "date", sortDir: "desc" },
  { labelKey: "tradeFilters.sortOldest", sortBy: "date", sortDir: "asc" },
  { labelKey: "sort.nameAZ", sortBy: "name", sortDir: "asc" },
  { labelKey: "sort.nameZA", sortBy: "name", sortDir: "desc" },
  { labelKey: "sort.set", sortBy: "set", sortDir: "asc" },
  { labelKey: "tradeFilters.sortStatus", sortBy: "status", sortDir: "asc" },
];

export const MATCH_SORT_OPTIONS: SortOption[] = [
  { labelKey: "sort.nameAZ", sortBy: "name", sortDir: "asc" },
  { labelKey: "sort.nameZA", sortBy: "name", sortDir: "desc" },
  { labelKey: "sort.set", sortBy: "set", sortDir: "asc" },
];
