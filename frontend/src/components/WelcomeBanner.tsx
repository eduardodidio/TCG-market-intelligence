import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

interface WelcomeBannerProps {
  onDismiss: () => void;
}

const STEPS = [
  {
    titleKey: "onboarding.step1Title",
    descKey: "onboarding.step1Desc",
    to: "/collection",
    icon: (
      <svg className="h-8 w-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
  },
  {
    titleKey: "onboarding.step2Title",
    descKey: "onboarding.step2Desc",
    to: "/market",
    icon: (
      <svg className="h-8 w-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
  },
  {
    titleKey: "onboarding.step3Title",
    descKey: "onboarding.step3Desc",
    to: "/decks",
    icon: (
      <svg className="h-8 w-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
] as const;

export function WelcomeBanner({ onDismiss }: WelcomeBannerProps) {
  const { t } = useTranslation();

  return (
    <div
      className="relative bg-slate-800 border border-cyan-500/30 rounded-lg p-6 mb-8"
      data-testid="welcome-banner"
    >
      {/* Dismiss button */}
      <button
        onClick={onDismiss}
        className="absolute top-3 right-3 text-slate-400 hover:text-white transition-colors"
        aria-label={t("onboarding.dismiss")}
        data-testid="welcome-dismiss"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <h2 className="text-xl font-bold text-white mb-1" data-testid="welcome-title">
        {t("onboarding.welcomeTitle")}
      </h2>
      <p className="text-sm text-slate-400 mb-6" data-testid="welcome-subtitle">
        {t("onboarding.welcomeSubtitle")}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {STEPS.map((step) => (
          <Link
            key={step.to}
            to={step.to}
            className="flex flex-col items-center text-center p-4 rounded-lg bg-slate-700/50 hover:bg-slate-700 border border-slate-600 hover:border-cyan-400/40 transition-all"
            data-testid={`welcome-step-${step.to.slice(1)}`}
          >
            <div className="mb-3">{step.icon}</div>
            <h3 className="text-sm font-semibold text-white mb-1">
              {t(step.titleKey)}
            </h3>
            <p className="text-xs text-slate-400">{t(step.descKey)}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
