import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { LanguageSelector } from "../components/LanguageSelector";

export function Login() {
  const { t } = useTranslation();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const { login, register, error: authError } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get("returnTo") || "/collection";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);

    try {
      let err: string | null;
      if (isRegister) {
        err = await register(email, password, displayName || undefined);
      } else {
        err = await login(email, password);
      }

      if (!err) {
        navigate(returnTo, { replace: true });
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

  const inputClasses = "w-full px-3 py-2 bg-tcg-card-alt border border-tcg-border rounded-tcg-md text-white placeholder-tcg-dimmed focus:outline-none focus:ring-2 focus:ring-tcg-primary transition-colors";

  return (
    <div className="min-h-screen flex items-center justify-center bg-tcg-bg px-4 relative">
      <div className="absolute top-4 right-4" data-testid="login-language-selector">
        <LanguageSelector variant="full" />
      </div>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold bg-tcg-gradient-hero bg-clip-text text-transparent">TCG Market</h1>
          <p className="text-tcg-muted mt-2">
            {isRegister ? t("auth.createAccount") : t("auth.signInAccount")}
          </p>
        </div>

        <div className="bg-tcg-surface rounded-tcg-xl border border-tcg-border p-8 shadow-tcg-lg">
          <form onSubmit={handleSubmit} data-testid="auth-form">
            {displayError && (
              <div
                className="mb-4 p-3 rounded-tcg-md bg-red-900/30 border border-red-700/50 text-tcg-loss text-sm"
                data-testid="auth-error"
              >
                {displayError}
              </div>
            )}

            {isRegister && (
              <div className="mb-4">
                <label
                  htmlFor="displayName"
                  className="block text-sm font-medium text-tcg-muted mb-1"
                >
                  {t("auth.displayName")}
                </label>
                <input
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className={inputClasses}
                  placeholder={t("auth.displayNamePlaceholder")}
                  data-testid="display-name-input"
                />
              </div>
            )}

            <div className="mb-4">
              <label
                htmlFor="email"
                className="block text-sm font-medium text-tcg-muted mb-1"
              >
                {t("auth.email")}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className={inputClasses}
                placeholder={t("auth.emailPlaceholder")}
                data-testid="email-input"
              />
            </div>

            <div className="mb-6">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-tcg-muted mb-1"
              >
                {t("auth.password")}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className={inputClasses}
                placeholder={t("auth.passwordPlaceholder")}
                data-testid="password-input"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 px-4 bg-tcg-gradient-hero hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-tcg-md transition-all focus:outline-none focus:ring-2 focus:ring-tcg-primary shadow-tcg-glow"
              data-testid="submit-button"
            >
              {submitting
                ? t("common.pleaseWait")
                : isRegister
                  ? t("auth.createAccountBtn")
                  : t("auth.signIn")}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setIsRegister(!isRegister);
                setFormError(null);
              }}
              className="text-sm text-tcg-primary-hover hover:text-tcg-accent transition-colors"
              data-testid="toggle-mode"
            >
              {isRegister
                ? t("auth.alreadyHaveAccount")
                : t("auth.dontHaveAccount")}
            </button>
          </div>

          {/* OAuth buttons placeholder */}
          <div className="mt-6 pt-6 border-t border-tcg-border">
            <p className="text-xs text-tcg-dimmed text-center mb-3">
              {t("auth.orContinueWith")}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                disabled
                className="flex-1 py-2 px-3 bg-tcg-card border border-tcg-border rounded-tcg-md text-tcg-dimmed text-sm font-medium cursor-not-allowed opacity-50"
                data-testid="oauth-google"
              >
                Google
              </button>
              <button
                type="button"
                disabled
                className="flex-1 py-2 px-3 bg-tcg-card border border-tcg-border rounded-tcg-md text-tcg-dimmed text-sm font-medium cursor-not-allowed opacity-50"
                data-testid="oauth-microsoft"
              >
                Microsoft
              </button>
              <button
                type="button"
                disabled
                className="flex-1 py-2 px-3 bg-tcg-card border border-tcg-border rounded-tcg-md text-tcg-dimmed text-sm font-medium cursor-not-allowed opacity-50"
                data-testid="oauth-apple"
              >
                Apple
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
