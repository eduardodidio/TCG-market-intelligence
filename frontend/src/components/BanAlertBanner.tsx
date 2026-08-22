import { useTranslation } from "react-i18next";

interface BanAlertBannerProps {
  bannedCount: number;
  restrictedCount: number;
  recentlyChangedCount: number;
  onDismiss: () => void;
}

export function BanAlertBanner({
  bannedCount,
  restrictedCount,
  recentlyChangedCount,
  onDismiss,
}: BanAlertBannerProps) {
  const { t } = useTranslation();

  if (bannedCount === 0 && restrictedCount === 0) {
    return null;
  }

  const hasBanned = bannedCount > 0;
  const bgClass = hasBanned
    ? "bg-red-900/30 border-red-700 text-red-200"
    : "bg-amber-900/30 border-amber-700 text-amber-200";

  return (
    <div
      data-testid="ban-alert-banner"
      className={`flex items-center gap-3 rounded-lg border p-4 ${bgClass}`}
      role="alert"
    >
      {/* Warning icon */}
      <svg
        className="h-5 w-5 flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>

      {/* Text content */}
      <div className="flex-1 text-sm">
        <span>
          {bannedCount > 0 && t("banEngine.alertBanned", { count: bannedCount })}
          {bannedCount > 0 && restrictedCount > 0 && ", "}
          {restrictedCount > 0 && t("banEngine.alertRestricted", { count: restrictedCount })}
        </span>
        {recentlyChangedCount > 0 && (
          <span className="ml-1 opacity-80">
            ({t("banEngine.alertRecent", { count: recentlyChangedCount })})
          </span>
        )}
      </div>

      {/* Dismiss button */}
      <button
        type="button"
        onClick={onDismiss}
        data-testid="ban-alert-dismiss"
        className="flex-shrink-0 rounded-md p-1 hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30"
        aria-label={t("banEngine.alertDismiss")}
      >
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
