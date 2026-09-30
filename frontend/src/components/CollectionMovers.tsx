import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  fetchCollectionMovers,
  type CollectionMoverData,
  type CollectionMoversData,
} from "../api/collection";
import { formatCurrency } from "../utils/format";

export interface MoverRowProps {
  mover: CollectionMoverData;
  type: "gainer" | "loser";
  onDismiss?: (cardId: number) => void;
}

export function MoverRow({ mover, type, onDismiss }: MoverRowProps) {
  const { t } = useTranslation();
  const colorClass = type === "gainer" ? "text-emerald-400" : "text-red-400";
  const sign = type === "gainer" ? "+" : "";

  return (
    <Link
      to={`/cards/${mover.card_id}`}
      className="group flex items-center gap-3 py-2 border-b border-slate-700/50 last:border-0
        hover:bg-slate-700/30 rounded px-1 -mx-1 transition-colors no-underline"
      data-testid={`mover-row-${type}`}
    >
      {mover.image_uri ? (
        <img
          src={mover.image_uri}
          alt={mover.card_name}
          className="h-10 w-7 rounded object-cover flex-shrink-0"
        />
      ) : (
        <div className="h-10 w-7 rounded bg-slate-700 flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-200 truncate">{mover.card_name}</p>
        {mover.set_code && (
          <p className="text-xs text-slate-500 uppercase">{mover.set_code}</p>
        )}
      </div>
      <div className="text-right flex-shrink-0">
        <p className={`text-sm font-medium ${colorClass}`}>
          {sign}{formatCurrency(mover.change_abs, "BRL")}
        </p>
        <p className={`text-xs ${colorClass}`}>
          {sign}{mover.change_pct.toFixed(1)}%
        </p>
      </div>
      {onDismiss && (
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDismiss(mover.card_id);
          }}
          className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity"
          aria-label={t("movers.dismiss")}
          data-testid={`mover-dismiss-${mover.card_id}`}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </Link>
  );
}

interface CollectionMoversProps {
  days?: number;
  limit?: number;
  investmentOnly?: boolean;
}

export function CollectionMovers({ days = 7, limit = 5, investmentOnly = false }: CollectionMoversProps) {
  const { t } = useTranslation();
  const [data, setData] = useState<CollectionMoversData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [currentLimit, setCurrentLimit] = useState(limit);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  const handleDismiss = useCallback((cardId: number) => {
    setDismissed((prev) => new Set(prev).add(cardId));
  }, []);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(false);
    fetchCollectionMovers(days, currentLimit, investmentOnly)
      .then((res) => {
        if (res.data) setData(res.data);
      })
      .catch(() => {
        setError(true);
      })
      .finally(() => setLoading(false));
  }, [days, currentLimit, investmentOnly]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="movers-loading">
        {[1, 2].map((i) => (
          <div key={i} className="animate-pulse bg-slate-700/50 rounded-lg h-48" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="bg-slate-800/50 border border-red-500/30 rounded-lg p-4 text-center"
        data-testid="movers-error"
      >
        <p className="text-sm text-red-400">{t("movers.error")}</p>
        <button
          onClick={fetchData}
          className="mt-2 text-xs text-indigo-400 hover:text-indigo-300"
        >
          {t("common.retry")}
        </button>
      </div>
    );
  }

  if (!data || (data.gainers.length === 0 && data.losers.length === 0)) {
    return (
      <div
        className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-center"
        data-testid="movers-empty"
      >
        <p className="text-sm text-slate-400">{t("movers.noData")}</p>
      </div>
    );
  }

  return (
    <div data-testid="collection-movers">
      <h3 className="text-sm font-medium text-slate-400 mb-3">
        {t("movers.title")}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Gainers column */}
        <div
          className="bg-slate-800 rounded-lg p-4 border border-slate-600"
          data-testid="movers-gainers"
        >
          <h4 className="text-sm font-semibold text-emerald-400 mb-2">
            {t("movers.gainers")}
          </h4>
          {data.gainers.filter((m) => !dismissed.has(m.card_id)).length > 0 ? (
            data.gainers
              .filter((m) => !dismissed.has(m.card_id))
              .map((m) => (
                <MoverRow key={m.card_id} mover={m} type="gainer" onDismiss={handleDismiss} />
              ))
          ) : (
            <p className="text-xs text-slate-500 py-2">{t("movers.noData")}</p>
          )}
        </div>

        {/* Losers column */}
        <div
          className="bg-slate-800 rounded-lg p-4 border border-slate-600"
          data-testid="movers-losers"
        >
          <h4 className="text-sm font-semibold text-red-400 mb-2">
            {t("movers.losers")}
          </h4>
          {data.losers.filter((m) => !dismissed.has(m.card_id)).length > 0 ? (
            data.losers
              .filter((m) => !dismissed.has(m.card_id))
              .map((m) => (
                <MoverRow key={m.card_id} mover={m} type="loser" onDismiss={handleDismiss} />
              ))
          ) : (
            <p className="text-xs text-slate-500 py-2">{t("movers.noData")}</p>
          )}
        </div>
      </div>
      <div className="flex justify-center gap-3 mt-3">
        {currentLimit < 10 && (
          <button
            onClick={() => setCurrentLimit(10)}
            className="text-xs text-indigo-400 hover:text-indigo-300"
            data-testid="movers-show-top10"
          >
            {t("movers.showTop10")}
          </button>
        )}
        {currentLimit >= 10 && currentLimit < 100 && (
          <button
            onClick={() => setCurrentLimit(100)}
            className="text-xs text-indigo-400 hover:text-indigo-300"
            data-testid="movers-show-top100"
          >
            {t("movers.showTop100")}
          </button>
        )}
        {currentLimit > limit && (
          <button
            onClick={() => setCurrentLimit(limit)}
            className="text-xs text-slate-500 hover:text-slate-400"
            data-testid="movers-collapse"
          >
            {t("movers.collapse")}
          </button>
        )}
      </div>
    </div>
  );
}
