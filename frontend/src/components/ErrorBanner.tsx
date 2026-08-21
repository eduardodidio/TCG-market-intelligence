import { useTranslation } from "react-i18next";

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  variant?: "full" | "inline";
}

const NETWORK_ERROR_MESSAGE =
  "Unable to connect to the server. Please check your connection.";

function isNetworkError(message: string): boolean {
  return (
    message.toLowerCase().includes("failed to fetch") ||
    message.toLowerCase().includes("networkerror") ||
    message.toLowerCase().includes("network error") ||
    message.toLowerCase().includes("load failed")
  );
}

export function ErrorBanner({
  message,
  onRetry,
  variant = "inline",
}: ErrorBannerProps) {
  const { t } = useTranslation();
  const displayMessage = isNetworkError(message)
    ? t("common.networkError")
    : message;

  if (variant === "full") {
    return (
      <div
        data-testid="error-banner"
        data-variant="full"
        className="flex flex-col items-center justify-center py-12 text-center"
        role="alert"
      >
        {/* Error icon */}
        <svg
          className="h-12 w-12 text-red-400 mb-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
          />
        </svg>
        <p className="text-red-400 text-lg mb-2">{displayMessage}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 rounded-md bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {t("common.retry")}
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      data-testid="error-banner"
      data-variant="inline"
      className="rounded-md bg-red-900/20 border border-red-700/50 p-4"
      role="alert"
    >
      <div className="flex items-center justify-between gap-4">
        <p className="text-red-400 text-sm">{displayMessage}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="shrink-0 rounded-md bg-red-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {t("common.retry")}
          </button>
        )}
      </div>
    </div>
  );
}
