import { useTranslation } from "react-i18next";
import { useTheme } from "../hooks/useTheme";
import type { Theme } from "../contexts/ThemeContext";

const THEME_CYCLE: Theme[] = ["dark", "light", "system"];

function SunIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 7.66l-.71-.71M4.05 4.05l-.71-.71M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  );
}

function MonitorIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

const THEME_ICONS: Record<Theme, typeof SunIcon> = {
  light: SunIcon,
  dark: MoonIcon,
  system: MonitorIcon,
};

export function ThemeToggle() {
  const { t } = useTranslation();
  const { theme, setTheme } = useTheme();

  return (
    <div
      className="flex rounded-md overflow-hidden border border-slate-500 dark:border-slate-500 border-gray-300"
      role="group"
      aria-label={t("theme.selector")}
      data-testid="theme-toggle"
    >
      {THEME_CYCLE.map((opt) => {
        const Icon = THEME_ICONS[opt];
        const isActive = theme === opt;
        return (
          <button
            key={opt}
            onClick={() => setTheme(opt)}
            className={`px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 flex items-center gap-1 ${
              isActive
                ? "bg-indigo-500 text-white"
                : "bg-white dark:bg-slate-800 text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-700 dark:hover:text-white"
            }`}
            aria-pressed={isActive}
            data-testid={`theme-btn-${opt}`}
            title={t(`theme.${opt}`)}
          >
            <Icon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{t(`theme.${opt}`)}</span>
          </button>
        );
      })}
    </div>
  );
}
