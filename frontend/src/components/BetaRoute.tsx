import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTranslation } from "react-i18next";
import { LoadingSpinner } from "./LoadingSpinner";

interface BetaRouteProps {
  children: React.ReactNode;
  requiresAuth?: boolean;
}

export function BetaRoute({ children, requiresAuth = true }: BetaRouteProps) {
  const { isAuthenticated, loading, hasBetaAccess } = useAuth();
  const { t } = useTranslation();
  const location = useLocation();

  if (loading) {
    return <LoadingSpinner message="Checking access..." />;
  }

  if (requiresAuth && !isAuthenticated) {
    const returnTo = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?returnTo=${returnTo}`} replace />;
  }

  if (!hasBetaAccess) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center p-8 bg-white dark:bg-slate-800 rounded-lg shadow-lg max-w-md" data-testid="beta-blocked-message">
          <div className="text-4xl mb-4" aria-hidden="true">&#x1F512;</div>
          <p className="text-gray-600 dark:text-slate-400 text-lg">
            {t("beta.blocked")}
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
