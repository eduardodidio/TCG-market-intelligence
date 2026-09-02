import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "./useAuth";
import { fetchCollection } from "../api/collection";

/**
 * Returns a Set of card_ids that the current user owns.
 * - Returns empty Set for unauthenticated users.
 * - Fetches collection once and caches until window regains focus.
 */
export function useOwnedCardIds(): Set<number> {
  const { isAuthenticated } = useAuth();
  const [ownedIds, setOwnedIds] = useState<Set<number>>(new Set());
  const fetchedRef = useRef(false);

  const load = useCallback(async () => {
    if (!isAuthenticated) {
      setOwnedIds(new Set());
      return;
    }
    try {
      const resp = await fetchCollection({ limit: "9999" });
      if (resp.data) {
        const ids = new Set<number>();
        for (const card of resp.data) {
          if (card.card_id != null) {
            ids.add(card.card_id);
          }
        }
        setOwnedIds(ids);
      }
    } catch {
      // Silently fail — badge is non-critical
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!fetchedRef.current) {
      fetchedRef.current = true;
      load();
    }
  }, [load]);

  // Re-fetch on window focus
  useEffect(() => {
    const handler = () => {
      if (document.visibilityState === "visible") {
        load();
      }
    };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, [load]);

  return ownedIds;
}
