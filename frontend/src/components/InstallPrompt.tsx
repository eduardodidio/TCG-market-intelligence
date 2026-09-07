import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";

const DISMISS_KEY = "tcg_install_dismissed_at";
const DISMISS_DURATION_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function isStandalone(): boolean {
  try {
    return (
      (typeof window.matchMedia === "function" &&
        window.matchMedia("(display-mode: standalone)").matches) ||
      ("standalone" in navigator &&
        (navigator as { standalone?: boolean }).standalone === true)
    );
  } catch {
    return false;
  }
}

function isDismissedRecently(): boolean {
  try {
    const dismissed = localStorage.getItem(DISMISS_KEY);
    if (!dismissed) return false;
    const ts = parseInt(dismissed, 10);
    return Date.now() - ts < DISMISS_DURATION_MS;
  } catch {
    return false;
  }
}

export function InstallPrompt() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);

      if (isAuthenticated && !isDismissedRecently()) {
        setVisible(true);
      }
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, [isAuthenticated]);

  // Show when user becomes authenticated and prompt is deferred
  useEffect(() => {
    if (isAuthenticated && deferredPrompt && !isDismissedRecently() && !isStandalone()) {
      setVisible(true);
    }
  }, [isAuthenticated, deferredPrompt]);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    if (choice.outcome === "accepted") {
      setVisible(false);
      setDeferredPrompt(null);
    }
  };

  const handleDismiss = () => {
    setVisible(false);
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      // ignore storage errors
    }
  };

  if (!visible) return null;

  return (
    <div
      className="flex items-center gap-3 rounded-lg bg-slate-700 border border-slate-600 px-4 py-3 text-sm text-slate-200 mx-4 mb-2"
      data-testid="install-prompt"
      role="banner"
    >
      <svg className="h-5 w-5 flex-shrink-0 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m0 0l-4-4m4 4l4-4" />
      </svg>
      <span className="flex-1">{t("pwa.installMessage")}</span>
      <button
        onClick={handleInstall}
        className="rounded-md bg-indigo-500 px-3 py-1 text-sm font-medium text-white hover:bg-indigo-400 transition-colors"
        data-testid="install-prompt-install"
      >
        {t("pwa.install")}
      </button>
      <button
        onClick={handleDismiss}
        className="text-slate-400 hover:text-white transition-colors"
        aria-label={t("pwa.dismiss")}
        data-testid="install-prompt-dismiss"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
