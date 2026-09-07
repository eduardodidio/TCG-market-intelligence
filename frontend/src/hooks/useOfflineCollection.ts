import { useCallback, useEffect, useState } from "react";
import { get, set } from "idb-keyval";
import { fetchCollection } from "../api/collection";
import type { CollectionCard } from "../types/api";

const IDB_KEY = "tcg_offline_collection";
const IDB_SYNC_KEY = "tcg_offline_collection_synced_at";

interface OfflineCollectionResult {
  data: CollectionCard[] | null;
  isOffline: boolean;
  lastSyncedAt: string | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useOfflineCollection(
  params?: Record<string, string>,
): OfflineCollectionResult {
  const [data, setData] = useState<CollectionCard[] | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchCollection(params);
      if (response.data) {
        setData(response.data);
        setIsOffline(false);

        const now = new Date().toISOString();
        setLastSyncedAt(now);

        // Persist to IndexedDB for offline access
        await set(IDB_KEY, response.data);
        await set(IDB_SYNC_KEY, now);
      }
    } catch {
      // Network failed — try IndexedDB fallback
      setIsOffline(true);
      try {
        const cached = await get<CollectionCard[]>(IDB_KEY);
        const syncedAt = await get<string>(IDB_SYNC_KEY);
        if (cached) {
          setData(cached);
          setLastSyncedAt(syncedAt ?? null);
        } else {
          setError("No cached data available");
        }
      } catch {
        setError("Failed to load offline data");
      }
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, isOffline, lastSyncedAt, loading, error, refresh: load };
}
