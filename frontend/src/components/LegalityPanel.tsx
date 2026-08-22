import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchEntryLegalities } from "../api/banEngine";
import { useApi } from "../hooks/useApi";
import { LegalityBadge } from "./LegalityBadge";
import type { CardLegalityWithChange } from "../types/api";

const DEFAULT_SHOWN = 8;

interface LegalityPanelProps {
  entryId: number;
  cardId: number | null;
}

export function LegalityPanel({ entryId, cardId }: LegalityPanelProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const fetcher = useCallback(() => {
    if (cardId == null) {
      return Promise.resolve({
        data: [] as CardLegalityWithChange[],
        meta: { cursor: null, total: null, offset: null, request_id: "" },
        errors: [],
      });
    }
    return fetchEntryLegalities(entryId);
  }, [entryId, cardId]);

  const { data: legalities, loading } = useApi<CardLegalityWithChange[]>(
    fetcher,
    [entryId, cardId],
  );

  if (cardId == null) {
    return (
      <div data-testid="legality-panel" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
        <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
          <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
          </svg>
          {t("banEngine.legalityTitle")}
        </h3>
        <p className="text-sm text-slate-400">{t("banEngine.legalityUnavailable")}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div data-testid="legality-panel" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
        <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
          <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
          </svg>
          {t("banEngine.legalityTitle")}
        </h3>
        <div className="animate-pulse flex gap-2 flex-wrap" data-testid="legality-skeleton">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-7 w-28 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!legalities || !Array.isArray(legalities) || legalities.length === 0) {
    return (
      <div data-testid="legality-panel" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
        <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
          <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
          </svg>
          {t("banEngine.legalityTitle")}
        </h3>
        <p className="text-sm text-slate-400">{t("banEngine.legalityEmpty")}</p>
      </div>
    );
  }

  // Safety guard: ensure legalities is an array
  const legalityList = Array.isArray(legalities) ? legalities : [];

  // Data is already sorted by the backend (banned > restricted > legal > not_legal)
  const shown = expanded ? legalityList : legalityList.slice(0, DEFAULT_SHOWN);
  const hasMore = legalityList.length > DEFAULT_SHOWN;

  return (
    <div data-testid="legality-panel" className="bg-slate-800 border border-slate-600 rounded-lg p-4">
      <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
        <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
        </svg>
        {t("banEngine.legalityTitle")}
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {shown.map((leg) => (
          <div key={leg.format} className="flex items-center gap-1.5">
            <LegalityBadge format={leg.format} status={leg.status} size="sm" />
            {leg.recently_changed && (
              <span
                className="bg-cyan-500/20 text-cyan-400 text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                data-testid={`legality-new-${leg.format}`}
                title={
                  leg.old_status && leg.change_date
                    ? t("banEngine.changedFrom", {
                        oldStatus: leg.old_status,
                        date: new Date(leg.change_date).toLocaleDateString(),
                      })
                    : t("banEngine.recentChange")
                }
              >
                {t("banEngine.newChip")}
              </span>
            )}
          </div>
        ))}
      </div>
      {hasMore && (
        <button
          data-testid="legality-panel-expand"
          onClick={() => setExpanded(!expanded)}
          className="mt-3 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {expanded
            ? t("banEngine.showLess")
            : t("banEngine.showAll", { count: legalityList.length })}
        </button>
      )}
    </div>
  );
}
