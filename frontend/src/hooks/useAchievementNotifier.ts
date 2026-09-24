import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { checkAchievements } from "../api/achievements";
import { fetchAchievements } from "../api/achievements";
import { notifyCreditsChanged } from "../utils/creditsEvents";
import type { AchievementItem } from "../types/achievements";

interface PendingToast {
  id: string;
  title: string;
  description: string;
  icon: string;
  reward?: number;
}

export function useAchievementNotifier() {
  const { t } = useTranslation();
  const [toasts, setToasts] = useState<PendingToast[]>([]);
  const checkingRef = useRef(false);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const triggerCheck = useCallback(async () => {
    // Prevent concurrent checks
    if (checkingRef.current) return;
    checkingRef.current = true;

    try {
      const resp = await checkAchievements();
      if (!resp.data) return;

      const { newly_unlocked, rewards, total_reward, backfilled } = resp.data;

      const newToasts: PendingToast[] = [];

      if (newly_unlocked.length > 0) {
        // Fetch full achievement data to get titles/descriptions
        const allResp = await fetchAchievements();
        if (allResp.data) {
          const defnMap = new Map<string, AchievementItem>();
          for (const a of allResp.data) {
            defnMap.set(a.key, a);
          }

          const rewardMap = new Map<string, number>();
          for (const r of rewards ?? []) {
            rewardMap.set(r.key, r.amount);
          }

          for (const key of newly_unlocked) {
            const defn = defnMap.get(key);
            if (defn) {
              newToasts.push({
                id: `${key}-${Date.now()}`,
                title: defn.title,
                description: defn.description,
                icon: defn.icon,
                reward: rewardMap.get(key),
              });
            }
          }
        }
      }

      if (backfilled && backfilled > 0) {
        newToasts.push({
          id: `backfill-${Date.now()}`,
          title: t("achievements.toastTitle"),
          description: t("achievements.backfillReward", { amount: backfilled }),
          icon: "treasure",
          reward: backfilled,
        });
      }

      if (newToasts.length > 0) {
        setToasts((prev) => [...prev, ...newToasts]);
      }

      if ((total_reward ?? 0) + (backfilled ?? 0) > 0) {
        notifyCreditsChanged();
      }
    } catch {
      // Silently fail — achievements are non-critical
    } finally {
      checkingRef.current = false;
    }
  }, [t]);

  return {
    toasts,
    dismissToast,
    checkAchievements: triggerCheck,
  };
}
