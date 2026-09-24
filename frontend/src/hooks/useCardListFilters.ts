import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useDebounce } from "./useDebounce";

export interface UseCardListFiltersOptions {
  defaultSortBy: string;
  defaultSortDir: "asc" | "desc";
}

export interface UseCardListFilters {
  search: string;
  setSearch: (v: string) => void;
  debouncedSearch: string;
  selectedSet: string | null;
  setSelectedSet: (v: string | null) => void;
  sortBy: string;
  sortDir: "asc" | "desc";
  sortValue: string;
  setSort: (sortBy: string, sortDir: "asc" | "desc") => void;
}

export function useCardListFilters({
  defaultSortBy,
  defaultSortDir,
}: UseCardListFiltersOptions): UseCardListFilters {
  const [searchParams, setSearchParams] = useSearchParams();

  const initialDir = searchParams.get("dir");
  const validInitialDir: "asc" | "desc" =
    initialDir === "asc" || initialDir === "desc" ? initialDir : defaultSortDir;

  const [search, setSearchState] = useState(searchParams.get("name") ?? "");
  const [selectedSet, setSelectedSetState] = useState<string | null>(
    searchParams.get("set") ?? null,
  );
  const [sortBy, setSortByState] = useState(searchParams.get("sort") ?? defaultSortBy);
  const [sortDir, setSortDirState] = useState<"asc" | "desc">(validInitialDir);

  const debouncedSearch = useDebounce(search, 300);

  const setSearch = useCallback(
    (v: string) => {
      setSearchState(v);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (v) {
            next.set("name", v);
          } else {
            next.delete("name");
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const setSelectedSet = useCallback(
    (v: string | null) => {
      setSelectedSetState(v);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (v) {
            next.set("set", v);
          } else {
            next.delete("set");
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const setSort = useCallback(
    (newSortBy: string, newSortDir: "asc" | "desc") => {
      setSortByState(newSortBy);
      setSortDirState(newSortDir);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (newSortBy && newSortBy !== defaultSortBy) {
            next.set("sort", newSortBy);
          } else {
            next.delete("sort");
          }
          if (newSortDir && newSortDir !== defaultSortDir) {
            next.set("dir", newSortDir);
          } else {
            next.delete("dir");
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams, defaultSortBy, defaultSortDir],
  );

  const sortValue = useMemo(() => `${sortBy}-${sortDir}`, [sortBy, sortDir]);

  return {
    search,
    setSearch,
    debouncedSearch,
    selectedSet,
    setSelectedSet,
    sortBy,
    sortDir,
    sortValue,
    setSort,
  };
}
