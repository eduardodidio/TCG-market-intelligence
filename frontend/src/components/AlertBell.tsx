import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useAlertNotifications } from "../hooks/useAlertNotifications";

function formatPrice(price: number | null): string {
  if (price === null) return "--";
  return `R$ ${price.toFixed(2)}`;
}

function timeAgo(dateStr: string, t: (key: string, options?: Record<string, unknown>) => string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return t("alerts.justNow");
  if (minutes < 60) return t("alerts.minutesAgo", { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t("alerts.hoursAgo", { count: hours });
  const days = Math.floor(hours / 24);
  return t("alerts.daysAgo", { count: days });
}

export function AlertBell() {
  const { t } = useTranslation();
  const { notifications, unreadCount, markAllRead } =
    useAlertNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClick);
    }
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div className="relative" ref={ref} data-testid="alert-bell">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        aria-label={t("alerts.bellLabel")}
        data-testid="alert-bell-button"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unreadCount > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full"
            data-testid="alert-badge"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 mt-2 w-80 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50"
          data-testid="alert-dropdown"
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-600">
            <h3 className="text-sm font-semibold text-white">
              {t("alerts.notifications")}
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={async () => {
                  await markAllRead();
                }}
                className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                data-testid="mark-all-read"
              >
                {t("alerts.markAllRead")}
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-slate-400">
                {t("alerts.noNotifications")}
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`px-4 py-3 border-b border-slate-700 last:border-0 ${
                    !n.is_read ? "bg-slate-750" : ""
                  }`}
                  data-testid="alert-notification-item"
                >
                  <div className="flex items-start gap-2">
                    {!n.is_read && (
                      <span className="mt-1.5 h-2 w-2 rounded-full bg-indigo-400 flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">
                        {n.card_name}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {formatPrice(n.old_price)} → {formatPrice(n.new_price)}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {timeAgo(n.notified_at, t)}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="px-4 py-2 border-t border-slate-600">
            <Link
              to="/alerts"
              onClick={() => setOpen(false)}
              className="block text-center text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              data-testid="view-all-alerts"
            >
              {t("alerts.viewAll")}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
