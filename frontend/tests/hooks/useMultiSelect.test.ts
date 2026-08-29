import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useMultiSelect } from "../../src/hooks/useMultiSelect";

describe("useMultiSelect", () => {
  it("starts with empty selection", () => {
    const { result } = renderHook(() => useMultiSelect());
    expect(result.current.count).toBe(0);
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("toggle adds an id", () => {
    const { result } = renderHook(() => useMultiSelect());
    act(() => result.current.toggle(1));
    expect(result.current.isSelected(1)).toBe(true);
    expect(result.current.count).toBe(1);
  });

  it("toggle removes an existing id", () => {
    const { result } = renderHook(() => useMultiSelect());
    act(() => result.current.toggle(1));
    act(() => result.current.toggle(1));
    expect(result.current.isSelected(1)).toBe(false);
    expect(result.current.count).toBe(0);
  });

  it("toggle multiple ids", () => {
    const { result } = renderHook(() => useMultiSelect());
    act(() => {
      result.current.toggle(1);
      result.current.toggle(2);
      result.current.toggle(3);
    });
    expect(result.current.count).toBe(3);
    expect(result.current.isSelected(1)).toBe(true);
    expect(result.current.isSelected(2)).toBe(true);
    expect(result.current.isSelected(3)).toBe(true);
  });

  it("selectAll adds all ids", () => {
    const { result } = renderHook(() => useMultiSelect());
    act(() => result.current.selectAll([10, 20, 30]));
    expect(result.current.count).toBe(3);
    expect(result.current.isSelected(10)).toBe(true);
    expect(result.current.isSelected(20)).toBe(true);
    expect(result.current.isSelected(30)).toBe(true);
  });

  it("selectAll replaces existing selection", () => {
    const { result } = renderHook(() => useMultiSelect());
    act(() => result.current.toggle(99));
    act(() => result.current.selectAll([1, 2]));
    expect(result.current.count).toBe(2);
    expect(result.current.isSelected(99)).toBe(false);
    expect(result.current.isSelected(1)).toBe(true);
  });

  it("deselectAll clears all", () => {
    const { result } = renderHook(() => useMultiSelect());
    act(() => result.current.selectAll([1, 2, 3]));
    act(() => result.current.deselectAll());
    expect(result.current.count).toBe(0);
    expect(result.current.isSelected(1)).toBe(false);
  });

  it("isSelected returns false for non-selected id", () => {
    const { result } = renderHook(() => useMultiSelect());
    expect(result.current.isSelected(999)).toBe(false);
  });

  it("count reflects current selection size", () => {
    const { result } = renderHook(() => useMultiSelect());
    expect(result.current.count).toBe(0);
    act(() => result.current.toggle(1));
    expect(result.current.count).toBe(1);
    act(() => result.current.toggle(2));
    expect(result.current.count).toBe(2);
    act(() => result.current.toggle(1));
    expect(result.current.count).toBe(1);
  });
});
