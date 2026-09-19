import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { get } from "idb-keyval";

function timeAgo(isoStr: string): string {
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const IDB_SYNC_KEY = "tcg_offline_collection_synced_at";

export function OfflineBanner() {
  const { t } = useTranslation();
  const [isOffline, setIsOffline] = useState(() =>
    typeof navigator !== "undefined" ? !navigator.onLine : false,
  );
  const [lastSynced, setLastSynced] = useState<string | null>(null);

  useEffect(() => {
    const goOffline = () => setIsOffline(true);
    const goOnline = () => setIsOffline(false);

    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);

    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, []);

  useEffect(() => {
    if (isOffline) {
      get<string>(IDB_SYNC_KEY).then((val) => {
        if (val) setLastSynced(val);
      }).catch(() => {});
    }
  }, [isOffline]);

  if (!isOffline) return null;

  return (
    <div
      className="flex items-center gap-2 bg-amber-600/90 px-4 py-2 text-sm text-white"
      data-testid="offline-banner"
      role="alert"
    >
      <svg className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636a9 9 0 010 12.728M5.636 18.364a9 9 0 010-12.728M12 9v4m0 4h.01" />
      </svg>
      <span>{t("pwa.offlineMessage")}</span>
      {lastSynced && (
        <span className="ml-2 text-amber-100/70 text-xs">
          ({t("pwa.lastSynced", { time: timeAgo(lastSynced) })})
        </span>
      )}
    </div>
  );
}
