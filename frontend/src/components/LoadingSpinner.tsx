import { useTranslation } from "react-i18next";

interface LoadingSpinnerProps {
  /** Optional message displayed below the spinner */
  message?: string;
}

export function LoadingSpinner({ message }: LoadingSpinnerProps) {
  const { t } = useTranslation();
  const displayMessage = message ?? t("common.loading");
  return (
    <div
      data-testid="loading-spinner"
      className="flex flex-col items-center justify-center py-12"
      role="status"
    >
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-tcg-border border-t-tcg-secondary" />
      <p className="mt-4 text-sm text-tcg-muted">{displayMessage}</p>
    </div>
  );
}
