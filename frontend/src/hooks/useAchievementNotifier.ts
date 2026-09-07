import { useCallback, useRef, useState } from "react";
import { checkAchievements } from "../api/achievements";
import { fetchAchievements } from "../api/achievements";
import type { AchievementItem } from "../types/achievements";

interface PendingToast {
  id: string;
  title: string;
  description: string;
  icon: string;
}

export function useAchievementNotifier() {
  const [toasts, setToasts] = useState<PendingToast[]>([]);
  const checkingRef = useRef(false);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const triggerCheck = useCallback(async () => {
    // Prevent concurrent checks
    if (checkingRef.current) return;
    checkingRef.current = true;

    try {
      const resp = await checkAchievements();
      if (!resp.data || resp.data.newly_unlocked.length === 0) return;

      // Fetch full achievement data to get titles/descriptions
      const allResp = await fetchAchievements();
      if (!allResp.data) return;

      const defnMap = new Map<string, AchievementItem>();
      for (const a of allResp.data) {
        defnMap.set(a.key, a);
      }

      const newToasts: PendingToast[] = [];
      for (const key of resp.data.newly_unlocked) {
        const defn = defnMap.get(key);
        if (defn) {
          newToasts.push({
            id: `${key}-${Date.now()}`,
            title: defn.title,
            description: defn.description,
            icon: defn.icon,
          });
        }
      }

      if (newToasts.length > 0) {
        setToasts((prev) => [...prev, ...newToasts]);
      }
    } catch {
      // Silently fail — achievements are non-critical
    } finally {
      checkingRef.current = false;
    }
  }, []);

  return {
    toasts,
    dismissToast,
    checkAchievements: triggerCheck,
  };
}
