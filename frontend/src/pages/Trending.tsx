import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useCurrency } from "../hooks/useCurrency";
import { useAuth } from "../hooks/useAuth";
import { TrendingSection } from "../components/TrendingSection";

const PERIODS = ["7d", "30d", "90d"] as const;
type Period = (typeof PERIODS)[number];

const LIMITS = ["10", "20", "50"] as const;

function isPeriod(value: string): value is Period {
  return (PERIODS as readonly string[]).includes(value);
}

export function Trending() {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialPeriod = searchParams.get("period") ?? "30d";
  const [period, setPeriod] = useState<Period>(
    isPeriod(initialPeriod) ? initialPeriod : "30d",
  );
  const [limit, setLimit] = useState<string>("20");
  const [collectionOnly, setCollectionOnly] = useState(true);

  useEffect(() => {
    document.title = `${t("trending.title")} | TCG Market`;
  }, [t]);

  // Persist period in URL
  useEffect(() => {
    const current = searchParams.get("period");
    if (current !== period) {
      setSearchParams({ period }, { replace: true });
    }
  }, [period, searchParams, setSearchParams]);

  return (
    <div data-testid="page-trending">
      <h1 className="mb-6 text-2xl font-bold text-white">{t("trending.title")}</h1>

      {/* Controls row */}
      <div className="mb-6 flex flex-wrap items-center gap-4">
        {/* Period selector */}
        <div
          className="flex rounded-md overflow-hidden"
          role="group"
          aria-label={t("trending.periodSelector")}
        >
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                p === period
                  ? "bg-indigo-500 text-white shadow-md"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Limit selector */}
        <select
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          aria-label={t("trending.resultsLimit")}
          className="rounded-md bg-slate-800 px-3 py-2 text-sm text-slate-400 border border-slate-600 focus:outline-none focus:border-indigo-500 focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {LIMITS.map((l) => (
            <option key={l} value={l}>
              {t("trending.topN", { n: l })}
            </option>
          ))}
        </select>

        {/* Collection-only toggle (authenticated users only) */}
        {isAuthenticated && (
          <label className="flex items-center gap-2 cursor-pointer" data-testid="collection-only-toggle">
            <input
              type="checkbox"
              checked={collectionOnly}
              onChange={(e) => setCollectionOnly(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-400 focus:ring-cyan-400"
            />
            <span className="text-sm text-slate-300">{t("trending.collectionOnly")}</span>
          </label>
        )}
      </div>

      {/* Trending sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <TrendingSection
          direction="gainers"
          period={period}
          currency={currency}
          limit={Number(limit)}
          variant="list"
          collectionOnly={isAuthenticated && collectionOnly}
        />
        <TrendingSection
          direction="losers"
          period={period}
          currency={currency}
          limit={Number(limit)}
          variant="list"
          collectionOnly={isAuthenticated && collectionOnly}
        />
      </div>
    </div>
  );
}
