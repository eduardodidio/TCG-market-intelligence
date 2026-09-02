import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Breadcrumb } from "../components/Breadcrumb";

export function ChangePassword() {
  const { t } = useTranslation();
  const { changePassword, error: authError } = useAuth();
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (newPassword !== confirmPassword) {
      setFormError(t("auth.passwordMismatch"));
      return;
    }

    if (newPassword.length < 8) {
      setFormError(t("auth.passwordTooShort"));
      return;
    }

    setSubmitting(true);
    try {
      const err = await changePassword(currentPassword, newPassword);
      if (!err) {
        navigate("/collection", { replace: true });
      } else {
        setFormError(err);
      }
    } catch {
      setFormError(t("auth.unexpectedError"));
    } finally {
      setSubmitting(false);
    }
  }

  const displayError = formError || authError;
  const inputClasses =
    "w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors";

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-slate-900 px-4"
      data-testid="page-change-password"
    >
      <div className="w-full max-w-md">
        <Breadcrumb
          items={[
            { label: t("nav.settings"), to: "/settings" },
            { label: t("auth.changePasswordTitle") },
          ]}
        />
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-500 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
            TEDHC Market
          </h1>
          <p className="text-slate-400 mt-2">{t("auth.changePasswordTitle")}</p>
        </div>

        <div className="bg-slate-800 rounded-xl border border-slate-600 p-8 shadow-lg">
          <div className="mb-4 p-3 rounded-md bg-amber-900/30 border border-amber-700/50 text-amber-400 text-sm">
            {t("auth.passwordExpiredMessage")}
          </div>

          <form onSubmit={handleSubmit} data-testid="change-password-form">
            {displayError && (
              <div
                className="mb-4 p-3 rounded-md bg-red-900/30 border border-red-700/50 text-red-400 text-sm"
                data-testid="change-password-error"
              >
                {displayError}
              </div>
            )}

            <div className="mb-4">
              <label
                htmlFor="currentPassword"
                className="block text-sm font-medium text-slate-400 mb-1"
              >
                {t("auth.currentPassword")}
              </label>
              <input
                id="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                className={inputClasses}
                data-testid="current-password-input"
              />
            </div>

            <div className="mb-4">
              <label
                htmlFor="newPassword"
                className="block text-sm font-medium text-slate-400 mb-1"
              >
                {t("auth.newPassword")}
              </label>
              <input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                className={inputClasses}
                data-testid="new-password-input"
              />
            </div>

            <div className="mb-6">
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-slate-400 mb-1"
              >
                {t("auth.confirmPassword")}
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                className={inputClasses}
                data-testid="confirm-password-input"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-500 via-purple-400 to-cyan-400 hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-md transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-md"
              data-testid="change-password-submit"
            >
              {submitting
                ? t("common.pleaseWait")
                : t("auth.changePasswordBtn")}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
