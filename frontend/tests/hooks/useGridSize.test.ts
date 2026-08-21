import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useGridSize } from "../../src/hooks/useGridSize";

const STORAGE_KEY = "tcg:grid-size";

describe("useGridSize", () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY);
  });

  it("returns 'md' when localStorage is empty", () => {
    const { result } = renderHook(() => useGridSize());
    expect(result.current.gridSize).toBe("md");
  });

  it("returns 'md' when localStorage has invalid value", () => {
    localStorage.setItem(STORAGE_KEY, "invalid");
    const { result } = renderHook(() => useGridSize());
    expect(result.current.gridSize).toBe("md");
  });

  it("returns stored value when localStorage has 'sm'", () => {
    localStorage.setItem(STORAGE_KEY, "sm");
    const { result } = renderHook(() => useGridSize());
    expect(result.current.gridSize).toBe("sm");
  });

  it("returns stored value when localStorage has 'lg'", () => {
    localStorage.setItem(STORAGE_KEY, "lg");
    const { result } = renderHook(() => useGridSize());
    expect(result.current.gridSize).toBe("lg");
  });

  it("setGridSize updates both state and localStorage", () => {
    const { result } = renderHook(() => useGridSize());
    expect(result.current.gridSize).toBe("md");

    act(() => {
      result.current.setGridSize("sm");
    });

    expect(result.current.gridSize).toBe("sm");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("sm");
  });
});
