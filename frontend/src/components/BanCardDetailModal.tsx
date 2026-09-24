import { useEffect, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { fetchCardBanHistory, fetchCardLegalities } from "../api/banlist";
import { useApi } from "../hooks/useApi";
import { useCardName } from "../hooks/useCardName";
import { scryfallImageUrl } from "../utils/scryfall";
import { LegalityBadge } from "./LegalityBadge";
import { StatusTransition } from "./StatusTransition";
import type { BanListEntry, CardBanHistoryEntry, CardLegality } from "../types/banlist";

export type ModalEntry = BanListEntry &
  Partial<{ owned: boolean; owned_quantity: number; printings: number }>;

interface BanCardDetailModalProps {
  entry: ModalEntry | null;
  onClose: () => void;
}

const SEVERITY_ORDER: Record<string, number> = {
  banned: 0,
  restricted: 1,
  legal: 2,
  not_legal: 3,
};

function sortLegalities(legalities: CardLegality[]): CardLegality[] {
  return [...legalities].sort((a, b) => {
    const sevA = SEVERITY_ORDER[a.status] ?? 4;
    const sevB = SEVERITY_ORDER[b.status] ?? 4;
    if (sevA !== sevB) return sevA - sevB;
    return a.format.localeCompare(b.format);
  });
}

function groupHistoryByFormat(
  history: CardBanHistoryEntry[],
  primaryFormat: string,
): Array<[string, CardBanHistoryEntry[]]> {
  const groups = new Map<string, CardBanHistoryEntry[]>();
  for (const item of history) {
    const existing = groups.get(item.format);
    if (existing) {
      existing.push(item);
    } else {
      groups.set(item.format, [item]);
    }
  }
  for (const events of groups.values()) {
    events.sort(
      (a, b) => new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime(),
    );
  }
  const formats = [...groups.keys()].sort((a, b) => {
    if (a === primaryFormat) return -1;
    if (b === primaryFormat) return 1;
    return a.localeCompare(b);
  });
  return formats.map((format) => [format, groups.get(format)!]);
}

function formatDate(isoDate: string, locale: string): string {
  try {
    return new Date(isoDate).toLocaleDateString(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return isoDate;
  }
}

export function BanCardDetailModal({ entry, onClose }: BanCardDetailModalProps) {
  const { t, i18n } = useTranslation();
  const { getCardName } = useCardName();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const legalitiesFetcher = useMemo(() => {
    if (!entry) return () => Promise.resolve({ data: [], meta: { cursor: null, total: null, offset: null, request_id: "" }, errors: [] });
    return () => fetchCardLegalities(entry.card_id);
  }, [entry]);

  const historyFetcher = useMemo(() => {
    if (!entry) return () => Promise.resolve({ data: [], meta: { cursor: null, total: null, offset: null, request_id: "" }, errors: [] });
    return () => fetchCardBanHistory(entry.card_id);
  }, [entry]);

  const {
    data: legalities,
    loading: legalitiesLoading,
    error: legalitiesError,
  } = useApi<CardLegality[]>(legalitiesFetcher, [entry?.card_id ?? null]);

  const {
    data: history,
    loading: historyLoading,
    error: historyError,
  } = useApi<CardBanHistoryEntry[]>(historyFetcher, [entry?.card_id ?? null]);

  useEffect(() => {
    if (!entry) return;
    closeButtonRef.current?.focus();
  }, [entry]);

  useEffect(() => {
    if (!entry) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [entry, onClose]);

  if (!entry) return null;

  const displayName = getCardName(entry.name_en, entry.name_pt, entry.name_en || undefined);
  const imageUrl =
    entry.image_url ||
    (entry.set_code && entry.collector_number
      ? scryfallImageUrl(entry.set_code, entry.collector_number)
      : null);
  const ownedQty = entry.owned_quantity ?? 0;
  const sortedLegalities = legalities ? sortLegalities(legalities) : null;
  const groupedHistory = history ? groupHistoryByFormat(history, entry.format) : null;
  const locale = i18n.language === "pt-BR" ? "pt-BR" : "en-US";

  return createPortal(
    <div
      className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="ban-card-modal-title"
      data-testid="ban-card-modal"
    >
      <div
        className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-slate-800 border border-slate-600 rounded-lg shadow-2xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          ref={closeButtonRef}
          onClick={onClose}
          className="absolute top-3 right-3 w-8 h-8 rounded-full bg-slate-700 text-white flex items-center justify-center hover:bg-slate-600 transition-colors"
          aria-label={t("banlist.detail.close")}
          data-testid="ban-card-modal-close"
        >
          &#x2715;
        </button>

        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          {imageUrl && (
            <img
              src={imageUrl}
              alt={displayName}
              className="w-32 rounded-lg shadow-lg flex-shrink-0 self-start"
              draggable={false}
            />
          )}
          <div className="min-w-0">
            <h2
              id="ban-card-modal-title"
              className="text-xl font-bold text-white mb-1"
            >
              {displayName}
            </h2>
            <p className="text-sm text-slate-400 mb-2">
              {entry.set_code?.toUpperCase()} #{entry.collector_number}
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              <LegalityBadge format={entry.format} status={entry.status} />
              {ownedQty > 0 && (
                <span
                  className="inline-flex items-center px-2 py-0.5 rounded border border-cyan-700 bg-cyan-900/30 text-cyan-400 text-xs font-medium"
                  data-testid="ban-card-owned-badge"
                >
                  {t("banlist.ownedQty", { count: ownedQty })}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-bold text-white mb-3">
            {t("banlist.detail.legalities")}
          </h3>
          <div data-testid="ban-card-legalities">
            {legalitiesLoading ? (
              <div className="animate-pulse flex gap-2 flex-wrap">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-7 w-28 bg-slate-700 rounded" />
                ))}
              </div>
            ) : legalitiesError ? (
              <p className="text-sm text-red-400">{legalitiesError}</p>
            ) : sortedLegalities && sortedLegalities.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
                {sortedLegalities.map((leg) => (
                  <LegalityBadge
                    key={leg.format}
                    format={leg.format}
                    status={leg.status}
                    size="sm"
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">{t("legality.unavailable")}</p>
            )}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-bold text-white mb-3">
            {t("banlist.detail.history")}
          </h3>
          <div data-testid="ban-card-history">
            {historyLoading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div
                    key={i}
                    className="animate-pulse bg-slate-700 rounded-lg h-16"
                  />
                ))}
              </div>
            ) : historyError ? (
              <p className="text-sm text-red-400">{historyError}</p>
            ) : groupedHistory && groupedHistory.length > 0 ? (
              <div className="space-y-4">
                {groupedHistory.map(([format, events]) => (
                  <div
                    key={format}
                    data-testid={`ban-card-history-format-${format}`}
                  >
                    <p className="text-sm font-semibold text-slate-300 mb-2 capitalize">
                      {format}
                    </p>
                    <div className="border-l-2 border-slate-600 ml-3 pl-4 space-y-3">
                      {events.map((ev) => (
                        <div key={ev.id} className="relative">
                          <StatusTransition
                            oldStatus={ev.old_status}
                            newStatus={ev.new_status}
                            size="sm"
                          />
                          <p className="text-xs text-slate-500 mt-1.5">
                            {ev.source === "scryfall_baseline"
                              ? t("banlist.detail.baseline")
                              : formatDate(ev.changed_at, locale)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p
                className="text-sm text-slate-400"
                data-testid="ban-card-history-empty"
              >
                {t("banlist.detail.noHistory")}
              </p>
            )}
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-700">
          <Link
            to={`/cards/${entry.card_id}`}
            className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            {t("banlist.detail.openCard")}
          </Link>
        </div>
      </div>
    </div>,
    document.body,
  );
}
