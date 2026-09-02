import { createContext, useCallback, useContext, useState } from "react";
import type { ReactNode } from "react";
import { deleteCollectionEntry } from "../api/collection";

export interface PendingDelete {
  entryId: number;
  entryName: string;
}

interface PendingDeleteContextValue {
  pendingDelete: PendingDelete | null;
  setPendingDelete: (pd: PendingDelete) => void;
  clearPendingDelete: () => void;
  executeDelete: () => Promise<void>;
}

const PendingDeleteContext = createContext<PendingDeleteContextValue>({
  pendingDelete: null,
  setPendingDelete: () => {},
  clearPendingDelete: () => {},
  executeDelete: async () => {},
});

export function PendingDeleteProvider({ children }: { children: ReactNode }) {
  const [pendingDelete, setPendingDeleteState] = useState<PendingDelete | null>(
    null,
  );

  const setPendingDelete = useCallback((pd: PendingDelete) => {
    setPendingDeleteState(pd);
  }, []);

  const clearPendingDelete = useCallback(() => {
    setPendingDeleteState(null);
  }, []);

  const executeDelete = useCallback(async () => {
    if (pendingDelete) {
      await deleteCollectionEntry(pendingDelete.entryId);
      setPendingDeleteState(null);
    }
  }, [pendingDelete]);

  return (
    <PendingDeleteContext.Provider
      value={{ pendingDelete, setPendingDelete, clearPendingDelete, executeDelete }}
    >
      {children}
    </PendingDeleteContext.Provider>
  );
}

export function usePendingDelete(): PendingDeleteContextValue {
  return useContext(PendingDeleteContext);
}
