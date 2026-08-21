import { useState, useCallback } from "react";
import type { GridSize } from "../utils/constants";

export type { GridSize };

const STORAGE_KEY = "tcg:grid-size";
const VALID_SIZES: GridSize[] = ["sm", "md", "lg"];

function readStoredSize(): GridSize {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && VALID_SIZES.includes(stored as GridSize)) {
      return stored as GridSize;
    }
  } catch {
    // localStorage unavailable
  }
  return "md";
}

export function useGridSize(): {
  gridSize: GridSize;
  setGridSize: (size: GridSize) => void;
} {
  const [gridSize, setGridSizeState] = useState<GridSize>(readStoredSize);

  const setGridSize = useCallback((size: GridSize) => {
    setGridSizeState(size);
    try {
      localStorage.setItem(STORAGE_KEY, size);
    } catch {
      // localStorage unavailable
    }
  }, []);

  return { gridSize, setGridSize };
}
