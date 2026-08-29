import { useCallback, useMemo, useState } from "react";

/**
 * Generic hook for multi-selection state management.
 * Works with any item that has a numeric `id` field.
 */
export function useMultiSelect() {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const toggle = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback((ids: number[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = useCallback(
    (id: number) => selectedIds.has(id),
    [selectedIds],
  );

  const count = useMemo(() => selectedIds.size, [selectedIds]);

  return { selectedIds, toggle, selectAll, deselectAll, isSelected, count };
}
