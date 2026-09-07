import { useTranslation } from "react-i18next";
import { useRegisterSW } from "virtual:pwa-register/react";

export function UpdatePrompt() {
  const { t } = useTranslation();
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW();

  if (!needRefresh) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-lg bg-indigo-600 px-4 py-3 text-sm text-white shadow-lg"
      data-testid="update-prompt"
      role="alert"
    >
      <span>{t("pwa.updateAvailable")}</span>
      <button
        onClick={() => updateServiceWorker(true)}
        className="rounded-md bg-white px-3 py-1 text-sm font-medium text-indigo-700 hover:bg-indigo-50 transition-colors"
        data-testid="update-prompt-update"
      >
        {t("pwa.update")}
      </button>
      <button
        onClick={() => setNeedRefresh(false)}
        className="text-indigo-200 hover:text-white transition-colors"
        aria-label={t("pwa.dismiss")}
        data-testid="update-prompt-dismiss"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
