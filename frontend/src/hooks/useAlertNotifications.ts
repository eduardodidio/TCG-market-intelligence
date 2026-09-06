import { useCallback, useEffect, useRef, useState } from "react";
import { fetchNotifications, markAllNotificationsRead } from "../api/alerts";
import type { AlertNotificationResponse } from "../types/alerts";

const POLL_INTERVAL_MS = 60_000;

interface UseAlertNotificationsResult {
  notifications: AlertNotificationResponse[];
  unreadCount: number;
  loading: boolean;
  markAllRead: () => Promise<void>;
  refetch: () => void;
}

export function useAlertNotifications(): UseAlertNotificationsResult {
  const [notifications, setNotifications] = useState<AlertNotificationResponse[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const doFetch = useCallback(async () => {
    try {
      const resp = await fetchNotifications({ limit: "10" });
      if (resp.data) {
        setNotifications(resp.data.notifications);
        setUnreadCount(resp.data.unread_count);
      }
    } catch {
      // Silently fail — polling will retry
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    doFetch();
    intervalRef.current = setInterval(doFetch, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [doFetch]);

  const markAllRead = useCallback(async () => {
    try {
      await markAllNotificationsRead();
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // Silently fail
    }
  }, []);

  return {
    notifications,
    unreadCount,
    loading,
    markAllRead,
    refetch: doFetch,
  };
}
