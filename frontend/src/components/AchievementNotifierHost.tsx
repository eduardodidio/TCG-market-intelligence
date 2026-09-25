import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useAchievementNotifier } from "../hooks/useAchievementNotifier";
import { AchievementToast } from "./AchievementToast";

const THROTTLE_MS = 30_000;

export function AchievementNotifierHost() {
  const { user, isAuthenticated } = useAuth();
  const location = useLocation();
  const { toasts, dismissToast, checkAchievements } = useAchievementNotifier();
  const lastCheckRef = useRef(0);

  const skip = !isAuthenticated || user?.role === "guest";

  useEffect(() => {
    if (skip) return;

    const now = Date.now();
    if (now - lastCheckRef.current < THROTTLE_MS) return;

    lastCheckRef.current = now;
    checkAchievements();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip, location.pathname]);

  if (skip || toasts.length === 0) return null;

  return (
    <div
      className="fixed top-4 left-1/2 -translate-x-1/2 z-[60] flex flex-col gap-2"
      data-testid="achievement-notifier-host"
    >
      {toasts.map((toast) => (
        <AchievementToast
          key={toast.id}
          title={toast.title}
          description={toast.description}
          icon={toast.icon}
          reward={toast.reward}
          inline
          onDismiss={() => dismissToast(toast.id)}
        />
      ))}
    </div>
  );
}
