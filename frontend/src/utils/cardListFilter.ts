export interface CardListAccessors<T> {
  name: (i: T) => string | null | undefined;
  namePt?: (i: T) => string | null | undefined;
  setCode: (i: T) => string | null | undefined;
  number?: (i: T) => string | null | undefined;
  price?: (i: T) => number | null | undefined;
  date?: (i: T) => string | null | undefined;
  status?: (i: T) => string | null | undefined;
}

function normalizeSearch(s: string): string {
  return s
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

export function filterCardList<T>(
  items: T[],
  f: { search?: string; set?: string | null; status?: string | null },
  acc: CardListAccessors<T>,
): T[] {
  const search = f.search?.trim();
  const normalizedSearch = search ? normalizeSearch(search) : "";
  const set = f.set?.toLowerCase();
  const status = f.status;

  return items.filter((item) => {
    if (normalizedSearch) {
      const name = acc.name(item);
      const namePt = acc.namePt?.(item);
      const matchesName = name ? normalizeSearch(name).includes(normalizedSearch) : false;
      const matchesNamePt = namePt ? normalizeSearch(namePt).includes(normalizedSearch) : false;
      if (!matchesName && !matchesNamePt) return false;
    }

    if (set) {
      const itemSet = acc.setCode(item);
      if (!itemSet || itemSet.toLowerCase() !== set) return false;
    }

    if (status && acc.status) {
      const itemStatus = acc.status(item);
      if (itemStatus !== status) return false;
    }

    return true;
  });
}

function compareNullableStrings(a: string | null | undefined, b: string | null | undefined, dir: "asc" | "desc"): number {
  const aEmpty = a === null || a === undefined || a === "";
  const bEmpty = b === null || b === undefined || b === "";
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;
  const result = a.localeCompare(b);
  return dir === "asc" ? result : -result;
}

function compareNullableNumbers(a: number | null | undefined, b: number | null | undefined, dir: "asc" | "desc"): number {
  const aEmpty = a === null || a === undefined;
  const bEmpty = b === null || b === undefined;
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;
  const result = a - b;
  return dir === "asc" ? result : -result;
}

function compareNaturalStrings(a: string | null | undefined, b: string | null | undefined, dir: "asc" | "desc"): number {
  const aEmpty = a === null || a === undefined || a === "";
  const bEmpty = b === null || b === undefined || b === "";
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;
  const result = a.localeCompare(b, undefined, { numeric: true });
  return dir === "asc" ? result : -result;
}

export function sortCardList<T>(
  items: T[],
  sortBy: string,
  sortDir: "asc" | "desc",
  acc: CardListAccessors<T>,
): T[] {
  const indexed = items.map((item, index) => ({ item, index }));

  let comparator: ((a: { item: T; index: number }, b: { item: T; index: number }) => number) | null = null;

  switch (sortBy) {
    case "name":
      comparator = (a, b) => compareNullableStrings(acc.name(a.item), acc.name(b.item), sortDir);
      break;
    case "set":
      comparator = (a, b) => compareNullableStrings(acc.setCode(a.item), acc.setCode(b.item), sortDir);
      break;
    case "number":
      if (acc.number) {
        const numberAcc = acc.number;
        comparator = (a, b) => compareNaturalStrings(numberAcc(a.item), numberAcc(b.item), sortDir);
      }
      break;
    case "price":
      if (acc.price) {
        const priceAcc = acc.price;
        comparator = (a, b) => compareNullableNumbers(priceAcc(a.item), priceAcc(b.item), sortDir);
      }
      break;
    case "date":
      if (acc.date) {
        const dateAcc = acc.date;
        comparator = (a, b) => compareNullableStrings(dateAcc(a.item), dateAcc(b.item), sortDir);
      }
      break;
    case "status":
      if (acc.status) {
        const statusAcc = acc.status;
        comparator = (a, b) => compareNullableStrings(statusAcc(a.item), statusAcc(b.item), sortDir);
      }
      break;
    default:
      comparator = null;
  }

  if (!comparator) {
    return items.slice();
  }

  const activeComparator = comparator;
  indexed.sort((a, b) => {
    const result = activeComparator(a, b);
    if (result !== 0) return result;
    return a.index - b.index;
  });

  return indexed.map((entry) => entry.item);
}

export function buildSetOptions<T>(items: T[], acc: CardListAccessors<T>): { label: string; value: string }[] {
  const seen = new Map<string, string>();

  for (const item of items) {
    const setCode = acc.setCode(item);
    if (!setCode) continue;
    const value = setCode.toLowerCase();
    if (!seen.has(value)) {
      seen.set(value, setCode.toUpperCase());
    }
  }

  return Array.from(seen.entries())
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}
