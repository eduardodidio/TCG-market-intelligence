import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { fetchBanHistoryPaginated, fetchFormats } from "../api/banlist";
import { useApi } from "../hooks/useApi";
import { BanEventCard } from "../components/BanEventCard";
import { scryfallImageUrl } from "../utils/scryfall";
import type { LegalityHistoryEntry } from "../types/banlist";

const PAGE_SIZE = 30;

function groupByMonth(
  items: LegalityHistoryEntry[],
): Map<string, LegalityHistoryEntry[]> {
  const groups = new Map<string, LegalityHistoryEntry[]>();
  for (const item of items) {
    const d = new Date(item.changed_at);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const existing = groups.get(key);
    if (existing) {
      existing.push(item);
    } else {
      groups.set(key, [item]);
    }
  }
  return groups;
}

function formatMonthYear(key: string, locale: string): string {
  const [year, month] = key.split("-");
  try {
    const d = new Date(Number(year), Number(month) - 1, 1);
    return d.toLocaleDateString(locale === "pt-BR" ? "pt-BR" : "en-US", {
      year: "numeric",
      month: "long",
    });
  } catch {
    return key;
  }
}

export function BanHistory() {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedFormat = searchParams.get("format") || "";
  const dateFrom = searchParams.get("dateFrom") || "";
  const dateTo = searchParams.get("dateTo") || "";

  const [allItems, setAllItems] = useState<LegalityHistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  // Formats list
  const formatsFetcher = useCallback(() => fetchFormats(), []);
  const { data: formats, loading: formatsLoading } = useApi<string[]>(
    formatsFetcher,
    [],
  );

  // Main data fetcher (initial load + filter changes)
  const mainFetcher = useCallback(
    () =>
      fetchBanHistoryPaginated({
        format: selectedFormat || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        limit: PAGE_SIZE,
        offset: 0,
      }),
    [selectedFormat, dateFrom, dateTo],
  );

  const { data: initialData, loading } = useApi(mainFetcher, [
    selectedFormat,
    dateFrom,
    dateTo,
  ]);

  // Reset accumulated items when filters change
  useEffect(() => {
    if (initialData) {
      setAllItems(initialData.items);
      setTotal(initialData.total);
      setOffset(initialData.items.length);
    }
  }, [initialData]);

  const handleLoadMore = useCallback(async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await fetchBanHistoryPaginated({
        format: selectedFormat || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      if (res.data) {
        setAllItems((prev) => [...prev, ...res.data!.items]);
        setTotal(res.data.total);
        setOffset((prev) => prev + res.data!.items.length);
      }
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, offset, selectedFormat, dateFrom, dateTo]);

  const setFilter = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams);
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const grouped = useMemo(() => groupByMonth(allItems), [allItems]);
  const hasMore = allItems.length < total;

  // Dot color for timeline
  const dotColor = (newStatus: string): string => {
    if (newStatus === "banned" || newStatus === "restricted") return "bg-red-500";
    if (newStatus === "legal") return "bg-green-500";
    return "bg-slate-500";
  };

  return (
    <div data-testid="page-ban-history">
      <h1 className="text-2xl font-bold text-white mb-1">
        {t("banHistory.title")}
      </h1>
      <p className="text-sm text-slate-400 mb-6">
        {t("banHistory.subtitle")}
      </p>

      {/* Filters */}
      <div
        className="flex flex-wrap items-end gap-4 mb-6"
        data-testid="ban-history-filters"
      >
        {/* Format selector */}
        <div>
          <label
            htmlFor="bh-format"
            className="block text-xs text-slate-400 mb-1"
          >
            {t("banlist.format")}
          </label>
          <select
            id="bh-format"
            data-testid="bh-format-select"
            value={selectedFormat}
            onChange={(e) => setFilter("format", e.target.value)}
            className="rounded-md bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
          >
            <option value="">{t("banHistory.allFormats")}</option>
            {formatsLoading && <option value="">...</option>}
            {formats?.map((f) => (
              <option key={f} value={f}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Date from */}
        <div>
          <label
            htmlFor="bh-date-from"
            className="block text-xs text-slate-400 mb-1"
          >
            {t("banHistory.dateFrom")}
          </label>
          <input
            id="bh-date-from"
            type="date"
            data-testid="bh-date-from"
            value={dateFrom}
            onChange={(e) => setFilter("dateFrom", e.target.value)}
            className="rounded-md bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
          />
        </div>

        {/* Date to */}
        <div>
          <label
            htmlFor="bh-date-to"
            className="block text-xs text-slate-400 mb-1"
          >
            {t("banHistory.dateTo")}
          </label>
          <input
            id="bh-date-to"
            type="date"
            data-testid="bh-date-to"
            value={dateTo}
            onChange={(e) => setFilter("dateTo", e.target.value)}
            className="rounded-md bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
          />
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div data-testid="ban-history-loading" className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="animate-pulse bg-slate-800 border border-slate-700 rounded-lg h-20"
            />
          ))}
        </div>
      ) : allItems.length === 0 ? (
        <div
          data-testid="ban-history-empty"
          className="text-slate-400 text-center py-12"
        >
          {t("banHistory.noEvents")}
        </div>
      ) : (
        <div data-testid="ban-history-timeline">
          {Array.from(grouped.entries()).map(([monthKey, events]) => (
            <div key={monthKey} className="mb-6">
              <h3
                className="text-lg font-semibold text-slate-300 mb-3"
                data-testid="month-group-header"
              >
                {formatMonthYear(monthKey, i18n.language)}
              </h3>
              <div className="border-l-2 border-slate-600 ml-3 pl-4 space-y-3">
                {events.map((ev, idx) => (
                  <div key={`${ev.card_id}-${ev.format}-${ev.changed_at}-${idx}`} className="relative">
                    {/* Timeline dot */}
                    <div
                      className={`absolute -left-[22px] top-4 w-2.5 h-2.5 rounded-full ${dotColor(ev.new_status)} ring-2 ring-slate-900`}
                      data-testid="timeline-dot"
                    />
                    <BanEventCard
                      event={{
                        cardId: ev.card_id,
                        nameEn: ev.name_en ?? undefined,
                        namePt: ev.name_pt ?? undefined,
                        setCode: ev.set_code ?? undefined,
                        collectorNumber: ev.collector_number ?? undefined,
                        format: ev.format,
                        oldStatus: ev.old_status,
                        newStatus: ev.new_status,
                        changedAt: ev.changed_at,
                        imageUrl:
                          ev.image_url ??
                          (ev.set_code && ev.collector_number
                            ? scryfallImageUrl(ev.set_code, ev.collector_number, "small")
                            : undefined),
                      }}
                      showCardInfo={true}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Pagination footer */}
          <div className="text-center mt-6 space-y-2">
            <p className="text-sm text-slate-400" data-testid="ban-history-count">
              {t("banHistory.showing", {
                loaded: allItems.length,
                total,
              })}
            </p>
            {hasMore && (
              <button
                data-testid="ban-history-load-more"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="inline-flex items-center gap-2 rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors disabled:opacity-50"
              >
                {loadingMore ? t("common.loading") : t("banHistory.loadMore")}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
