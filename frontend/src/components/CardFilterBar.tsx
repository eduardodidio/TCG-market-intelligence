import type { ReactNode } from "react";
import { SearchBar } from "./SearchBar";
import { SortSelect, type SortOption } from "./SortSelect";
import { SetIconFilter } from "./SetIconFilter";
import { GridSizeToggle } from "./GridSizeToggle";
import type { GridSize } from "../utils/constants";

export interface CardFilterBarProps {
  search: string;
  onSearchChange: (v: string) => void;
  searchPlaceholder?: string;
  sortOptions: SortOption[];
  sortValue: string;
  onSortChange: (sortBy: string, sortDir: "asc" | "desc") => void;
  setOptions?: { label: string; value: string }[];
  selectedSet?: string | null;
  onSetSelect?: (v: string | null) => void;
  gridSize?: GridSize;
  onGridSizeChange?: (s: GridSize) => void;
  actions?: ReactNode;
  children?: ReactNode;
  testId?: string;
}

export function CardFilterBar({
  search,
  onSearchChange,
  searchPlaceholder,
  sortOptions,
  sortValue,
  onSortChange,
  setOptions,
  selectedSet = null,
  onSetSelect,
  gridSize,
  onGridSizeChange,
  actions,
  children,
  testId = "sticky-filter-bar",
}: CardFilterBarProps) {
  const showSetFilter = Boolean(setOptions && setOptions.length > 0 && onSetSelect);
  const showActions = Boolean(gridSize && onGridSizeChange);

  return (
    <div
      className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur-sm pb-4 pt-2 -mx-6 px-6 border-b border-slate-700/50 space-y-4 mb-6"
      data-testid={testId}
    >
      <div className="flex gap-3 items-center">
        <div className="flex-1">
          <SearchBar value={search} onChange={onSearchChange} placeholder={searchPlaceholder} />
        </div>
        <SortSelect options={sortOptions} value={sortValue} onChange={onSortChange} />
      </div>
      {showSetFilter && (
        <SetIconFilter options={setOptions!} selected={selectedSet} onSelect={onSetSelect!} />
      )}
      {children}
      {showActions && (
        <div className="flex justify-end items-center gap-3" data-testid="filter-bar-actions">
          {actions}
          <GridSizeToggle value={gridSize!} onChange={onGridSizeChange!} />
        </div>
      )}
    </div>
  );
}
