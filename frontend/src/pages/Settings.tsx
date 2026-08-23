import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { useCurrency } from "../hooks/useCurrency";
import { useLanguage } from "../hooks/useLanguage";
import { CurrencyToggle } from "../components/CurrencyToggle";
import { LanguageSelector } from "../components/LanguageSelector";
import { apiPatch } from "../api/client";

export function Settings() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { currency } = useCurrency();
  const { language } = useLanguage();
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    document.title = `${t("settings.title")} | TCG Market`;
  }, [t]);

  // Persist preferences to backend when currency or language changes
  useEffect(() => {
    if (!user) return;
    const timer = setTimeout(() => {
      apiPatch("/api/v1/auth/me/preferences", {
        preferred_currency: currency,
        preferred_language: language,
      }).then(() => {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      });
    }, 500);
    return () => clearTimeout(timer);
  }, [currency, language, user]);

  return (
    <div data-testid="page-settings" className="max-w-2xl">
      <h2 className="text-2xl font-bold text-white mb-6">{t("settings.title")}</h2>

      {/* Account section */}
      <section className="mb-8" data-testid="settings-account">
        <h3 className="text-lg font-semibold text-white mb-4">{t("settings.account")}</h3>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4 space-y-3">
          <div>
            <label className="text-sm text-slate-400">{t("auth.email")}</label>
            <p className="text-white">{user?.email || t("common.noData")}</p>
          </div>
          <div>
            <label className="text-sm text-slate-400">{t("auth.displayName")}</label>
            <p className="text-white">{user?.display_name || t("common.noData")}</p>
          </div>
        </div>
      </section>

      {/* Preferences section */}
      <section className="mb-8" data-testid="settings-preferences">
        <h3 className="text-lg font-semibold text-white mb-4">{t("settings.preferences")}</h3>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4 space-y-4">
          <div>
            <label className="text-sm text-slate-400 block mb-2">{t("currency.selector")}</label>
            <CurrencyToggle />
          </div>
          <div>
            <label className="text-sm text-slate-400 block mb-2">{t("language.selector")}</label>
            <LanguageSelector variant="full" />
          </div>
        </div>
        {saved && (
          <p className="text-xs text-green-400 mt-2" data-testid="settings-saved">
            {t("settings.saved")}
          </p>
        )}
      </section>

      {/* Placeholder sections */}
      <section className="mb-8" data-testid="settings-api-keys">
        <h3 className="text-lg font-semibold text-white mb-4">{t("settings.apiKeys")}</h3>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
          <p className="text-sm text-slate-500">{t("settings.comingSoon")}</p>
        </div>
      </section>

      <section className="mb-8" data-testid="settings-export">
        <h3 className="text-lg font-semibold text-white mb-4">{t("settings.dataExport")}</h3>
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
          <p className="text-sm text-slate-500">{t("settings.comingSoon")}</p>
        </div>
      </section>
    </div>
  );
}
