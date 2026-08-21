import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function Login() {
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
      setFormError("An unexpected error occurred");
    } finally {
      setSubmitting(false);
    }
  }

  const displayError = formError || authError;

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">TCG Market</h1>
          <p className="text-slate-400 mt-2">
            {isRegister ? "Create your account" : "Sign in to your account"}
          </p>
        </div>

        <div className="bg-slate-800 rounded-xl border border-slate-700 p-8">
          <form onSubmit={handleSubmit} data-testid="auth-form">
            {displayError && (
              <div
                className="mb-4 p-3 rounded-lg bg-red-900/50 border border-red-700 text-red-300 text-sm"
                data-testid="auth-error"
              >
                {displayError}
              </div>
            )}

            {isRegister && (
              <div className="mb-4">
                <label
                  htmlFor="displayName"
                  className="block text-sm font-medium text-slate-300 mb-1"
                >
                  Display Name
                </label>
                <input
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Your name"
                  data-testid="display-name-input"
                />
              </div>
            )}

            <div className="mb-4">
              <label
                htmlFor="email"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="you@example.com"
                data-testid="email-input"
              />
            </div>

            <div className="mb-6">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Min. 8 characters"
                data-testid="password-input"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
              data-testid="submit-button"
            >
              {submitting
                ? "Please wait..."
                : isRegister
                  ? "Create Account"
                  : "Sign In"}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setIsRegister(!isRegister);
                setFormError(null);
              }}
              className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
              data-testid="toggle-mode"
            >
              {isRegister
                ? "Already have an account? Sign in"
                : "Don't have an account? Create one"}
            </button>
          </div>

          {/* OAuth buttons placeholder */}
          <div className="mt-6 pt-6 border-t border-slate-700">
            <p className="text-xs text-slate-500 text-center mb-3">
              Or continue with
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                disabled
                className="flex-1 py-2 px-3 bg-slate-700 border border-slate-600 rounded-lg text-slate-400 text-sm font-medium cursor-not-allowed opacity-50"
                data-testid="oauth-google"
              >
                Google
              </button>
              <button
                type="button"
                disabled
                className="flex-1 py-2 px-3 bg-slate-700 border border-slate-600 rounded-lg text-slate-400 text-sm font-medium cursor-not-allowed opacity-50"
                data-testid="oauth-microsoft"
              >
                Microsoft
              </button>
              <button
                type="button"
                disabled
                className="flex-1 py-2 px-3 bg-slate-700 border border-slate-600 rounded-lg text-slate-400 text-sm font-medium cursor-not-allowed opacity-50"
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
