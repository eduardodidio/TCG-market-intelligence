export const API_BASE_URL: string =
  (typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_API_BASE_URL as string) ||
  "";

export const DEFAULT_PAGE_LIMIT = 24;

export type GridSize = "sm" | "md" | "lg";

export const GRID_SIZE_CONFIG: Record<
  GridSize,
  { gridClasses: string; label: string; compact: boolean }
> = {
  sm: {
    gridClasses:
      "grid-cols-3 sm:grid-cols-4 md:grid-cols-5 xl:grid-cols-8 gap-3",
    label: "Small grid",
    compact: true,
  },
  md: {
    gridClasses:
      "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6 gap-4",
    label: "Medium grid",
    compact: false,
  },
  lg: {
    gridClasses:
      "grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-5",
    label: "Large grid",
    compact: false,
  },
};
