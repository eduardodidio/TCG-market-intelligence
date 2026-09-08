import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  fetchCollectionMovers,
  type CollectionMoverData,
  type CollectionMoversData,
} from "../api/collection";
import { formatCurrency } from "../utils/format";

interface MoverRowProps {
  mover: CollectionMoverData;
  type: "gainer" | "loser";
}

function MoverRow({ mover, type }: MoverRowProps) {
  const colorClass = type === "gainer" ? "text-emerald-400" : "text-red-400";
  const sign = type === "gainer" ? "+" : "";

  return (
    <div
      className="flex items-center gap-3 py-2 border-b border-slate-700/50 last:border-0"
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
    </div>
  );
}

interface CollectionMoversProps {
  days?: number;
  limit?: number;
}

export function CollectionMovers({ days = 7, limit = 5 }: CollectionMoversProps) {
  const { t } = useTranslation();
  const [data, setData] = useState<CollectionMoversData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchCollectionMovers(days, limit)
      .then((res) => {
        if (res.data) setData(res.data);
      })
      .finally(() => setLoading(false));
  }, [days, limit]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="movers-loading">
        {[1, 2].map((i) => (
          <div key={i} className="animate-pulse bg-slate-700/50 rounded-lg h-48" />
        ))}
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
          {data.gainers.length > 0 ? (
            data.gainers.map((m) => (
              <MoverRow key={m.card_id} mover={m} type="gainer" />
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
          {data.losers.length > 0 ? (
            data.losers.map((m) => (
              <MoverRow key={m.card_id} mover={m} type="loser" />
            ))
          ) : (
            <p className="text-xs text-slate-500 py-2">{t("movers.noData")}</p>
          )}
        </div>
      </div>
    </div>
  );
}
