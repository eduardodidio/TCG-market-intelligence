import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchBanList, fetchFormats } from "../api/banlist";
import { useApi } from "../hooks/useApi";
import { useCardName } from "../hooks/useCardName";
import { Breadcrumb } from "../components/Breadcrumb";
import { LegalityBadge } from "../components/LegalityBadge";
import { scryfallImageUrl } from "../utils/scryfall";
import type { BanListEntry } from "../types/banlist";

const STATUS_FILTERS = ["all", "banned", "restricted"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const PAGE_SIZE = 50;

export function BanList() {
  const { t } = useTranslation();
  const { getCardName } = useCardName();

  // Format list
  const formatsFetcher = useCallback(() => fetchFormats(), []);
  const { data: formats, loading: formatsLoading } = useApi<string[]>(
    formatsFetcher,
    [],
  );

  const [selectedFormat, setSelectedFormat] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Set default format when formats load
  useEffect(() => {
    if (formats && formats.length > 0 && !selectedFormat) {
      const preferred = formats.includes("standard") ? "standard" : formats[0];
      setSelectedFormat(preferred);
    }
  }, [formats, selectedFormat]);

  // Debounce search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  // Fetch ban list
  const banlistFetcher = useCallback(
    () => {
      if (!selectedFormat) {
        return Promise.resolve({
          data: [],
          meta: { cursor: null, total: null, offset: null, request_id: "" },
          errors: [],
        });
      }
      return fetchBanList({
        format: selectedFormat,
        status: statusFilter === "all" ? undefined : statusFilter,
        search: debouncedSearch || undefined,
        limit: PAGE_SIZE,
      });
    },
    [selectedFormat, statusFilter, debouncedSearch],
  );

  const {
    data: entries,
    loading: entriesLoading,
    error,
  } = useApi<BanListEntry[]>(banlistFetcher, [
    selectedFormat,
    statusFilter,
    debouncedSearch,
  ]);

  const sortedEntries = useMemo(() => {
    if (!entries) return [];
    // Sort: banned first, then restricted, then by name
    const statusOrder: Record<string, number> = {
      banned: 0,
      restricted: 1,
    };
    return [...entries].sort((a, b) => {
      const oa = statusOrder[a.status] ?? 2;
      const ob = statusOrder[b.status] ?? 2;
      if (oa !== ob) return oa - ob;
      return (a.name_en || "").localeCompare(b.name_en || "");
    });
  }, [entries]);

  return (
    <div data-testid="page-banlist">
      <Breadcrumb
        items={[
          { label: t("nav.dashboard"), to: "/" },
          { label: t("nav.banlist") },
        ]}
      />
      <h1 className="text-2xl font-bold text-white mb-6">
        {t("banlist.title")}
      </h1>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        {/* Format selector */}
        <div>
          <label
            htmlFor="format-select"
            className="block text-xs text-slate-400 mb-1"
          >
            {t("banlist.format")}
          </label>
          <select
            id="format-select"
            data-testid="format-select"
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
            className="rounded-md bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
          >
            {formatsLoading && (
              <option value="">{t("common.loading")}</option>
            )}
            {formats?.map((f) => (
              <option key={f} value={f}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Status filter */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            {t("banlist.status")}
          </label>
          <div className="flex gap-1" data-testid="status-filter">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  statusFilter === s
                    ? "bg-indigo-500 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
                }`}
                data-testid={`status-btn-${s}`}
              >
                {s === "all"
                  ? t("banlist.all")
                  : s === "banned"
                    ? t("banlist.banned")
                    : t("banlist.restricted")}
              </button>
            ))}
          </div>
        </div>

        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <label
            htmlFor="banlist-search"
            className="block text-xs text-slate-400 mb-1"
          >
            &nbsp;
          </label>
          <input
            id="banlist-search"
            data-testid="banlist-search"
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("banlist.search")}
            className="w-full rounded-md bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-400"
          />
        </div>
      </div>

      {/* Results */}
      {entriesLoading ? (
        <div className="text-slate-400 text-center py-12">
          {t("common.loading")}
        </div>
      ) : error ? (
        <div className="text-red-400 text-center py-12">{error}</div>
      ) : sortedEntries.length === 0 ? (
        <div
          data-testid="banlist-empty"
          className="text-slate-400 text-center py-12"
        >
          {t("banlist.no_results")}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {sortedEntries.map((entry) => (
            <BanListCard
              key={`${entry.card_id}-${entry.format}-${entry.status}`}
              entry={entry}
              getCardName={getCardName}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function BanListCard({
  entry,
  getCardName,
}: {
  entry: BanListEntry;
  getCardName: (
    nameEn: string | null | undefined,
    namePt: string | null | undefined,
    fallback: string,
  ) => string;
}) {
  const { t } = useTranslation();
  const displayName = getCardName(entry.name_en, entry.name_pt, t("common.unknownCard"));
  const imageUrl =
    entry.image_url ||
    (entry.set_code && entry.collector_number
      ? scryfallImageUrl(entry.set_code, entry.collector_number)
      : null);

  return (
    <div
      data-testid="banlist-card"
      className="bg-slate-800 border border-slate-600 rounded-lg overflow-hidden hover:border-slate-500 transition-colors"
    >
      {imageUrl && (
        <div className="aspect-[488/680] bg-slate-900">
          <img
            src={imageUrl}
            alt={displayName}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        </div>
      )}
      <div className="p-3">
        <p className="text-sm font-medium text-white truncate mb-1">
          {displayName}
        </p>
        <div className="flex items-center gap-2 mb-2">
          {entry.set_code && (
            <span className="text-xs font-mono text-slate-400">
              {entry.set_code.toUpperCase()}
            </span>
          )}
          {entry.collector_number && (
            <span className="text-xs text-slate-500">
              #{entry.collector_number}
            </span>
          )}
        </div>
        <LegalityBadge status={entry.status} size="sm" />
        {entry.effective_date && (
          <p className="text-xs text-slate-500 mt-1">
            {t("banlist.effective_date")}: {entry.effective_date}
          </p>
        )}
      </div>
    </div>
  );
}
