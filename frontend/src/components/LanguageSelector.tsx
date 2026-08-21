import { useTranslation } from "react-i18next";
import { useLanguage } from "../hooks/useLanguage";
import { useAuth } from "../hooks/useAuth";
import { apiPatch } from "../api/client";
import type { SupportedLanguage } from "../contexts/LanguageContext";

interface LanguageSelectorProps {
  variant?: "compact" | "full";
}

const LANGUAGE_OPTIONS: { code: SupportedLanguage; label: string; flag: string }[] = [
  { code: "en", label: "EN", flag: "US" },
  { code: "pt-BR", label: "PT-BR", flag: "BR" },
];

export function LanguageSelector({ variant = "compact" }: LanguageSelectorProps) {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const { isAuthenticated } = useAuth();

  async function handleLanguageChange(lang: SupportedLanguage) {
    setLanguage(lang);
    if (isAuthenticated) {
      try {
        await apiPatch("/api/v1/auth/me/preferences", {
          preferred_language: lang,
        });
      } catch {
        // Best-effort save -- language still updates locally
      }
    }
  }

  if (variant === "full") {
    return (
      <div
        className="flex rounded-md overflow-hidden border border-slate-500"
        role="group"
        aria-label={t("language.selector")}
        data-testid="language-selector"
      >
        {LANGUAGE_OPTIONS.map((opt) => (
          <button
            key={opt.code}
            onClick={() => handleLanguageChange(opt.code)}
            className={`px-4 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 flex items-center gap-1.5 ${
              language === opt.code
                ? "bg-indigo-500 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
            }`}
            aria-pressed={language === opt.code}
            data-testid={`language-btn-${opt.code}`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    );
  }

  // Compact variant (for sidebar)
  return (
    <div
      className="flex rounded-md overflow-hidden border border-slate-500"
      role="group"
      aria-label={t("language.selector")}
      data-testid="language-selector"
    >
      {LANGUAGE_OPTIONS.map((opt) => (
        <button
          key={opt.code}
          onClick={() => handleLanguageChange(opt.code)}
          className={`px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 flex items-center gap-1 ${
            language === opt.code
              ? "bg-indigo-500 text-white"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
          }`}
          aria-pressed={language === opt.code}
          data-testid={`language-btn-${opt.code}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
