import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <h1 className="text-6xl font-bold text-slate-400 mb-4">404</h1>
      <p className="text-xl text-slate-300 mb-6">
        {t("notFound.message", "Page not found")}
      </p>
      <Link
        to="/"
        className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
      >
        {t("notFound.backHome", "Back to Home")}
      </Link>
    </div>
  );
}
