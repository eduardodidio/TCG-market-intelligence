import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { fetchBanList, fetchBanlistStatus, fetchFormats } from "../api/banlist";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import { useCardName } from "../hooks/useCardName";
import { Breadcrumb } from "../components/Breadcrumb";
import { LegalityBadge } from "../components/LegalityBadge";
import { BanCardDetailModal } from "../components/BanCardDetailModal";
import { scryfallImageUrl } from "../utils/scryfall";
import type { BanListEntry, BanlistStatus } from "../types/banlist";

const STATUS_FILTERS = ["all", "banned", "restricted"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const PAGE_SIZE = 50;

export function BanList() {
  const { t, i18n } = useTranslation();
  const { getCardName } = useCardName();
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // Format list
  const formatsFetcher = useCallback(() => fetchFormats(), []);
  const { data: formats, loading: formatsLoading } = useApi<string[]>(
    formatsFetcher,
    [],
  );

  // Status (last synced, legalities count)
  const statusFetcher = useCallback(() => fetchBanlistStatus(), []);
  const { data: status } = useApi<BanlistStatus>(statusFetcher, []);

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<BanListEntry | null>(null);

  const selectedFormat = searchParams.get("format") || "";
  const ownedOnlyParam = searchParams.get("owned") === "1";
  const ownedOnly = isAuthenticated && ownedOnlyParam;

  // Set default format when formats load
  useEffect(() => {
    if (formats && formats.length > 0 && !selectedFormat) {
      const preferred = formats.includes("commander")
        ? "commander"
        : formats.includes("standard")
          ? "standard"
          : formats[0];
      const params = new URLSearchParams(searchParams);
      params.set("format", preferred);
      setSearchParams(params, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const toggleOwnedOnly = useCallback(() => {
    const params = new URLSearchParams(searchParams);
    if (ownedOnlyParam) {
      params.delete("owned");
    } else {
      params.set("owned", "1");
    }
    setSearchParams(params, { replace: true });
  }, [searchParams, setSearchParams, ownedOnlyParam]);

  const handleFormatChange = useCallback(
    (format: string) => {
      const params = new URLSearchParams(searchParams);
      params.set("format", format);
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  // Ban list data: paginated, appended via "load more"
  const [entries, setEntries] = useState<BanListEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [entriesLoading, setEntriesLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchCountRef = useRef(0);

  useEffect(() => {
    if (!selectedFormat) return;
    fetchCountRef.current += 1;
    const currentFetch = fetchCountRef.current;
    setEntriesLoading(true);
    setError(null);
    fetchBanList({
      format: selectedFormat,
      status: statusFilter === "all" ? undefined : statusFilter,
      search: debouncedSearch || undefined,
      limit: PAGE_SIZE,
      offset: 0,
      ownedOnly,
    })
      .then((res) => {
        if (currentFetch !== fetchCountRef.current) return;
        if (res.errors.length > 0) {
          setError(res.errors.map((e) => e.message).join("; "));
          setEntries([]);
          setTotal(0);
          setOffset(0);
          return;
        }
        const data = res.data ?? [];
        setEntries(data);
        setTotal(res.meta.total ?? data.length);
        setOffset(data.length);
      })
      .catch((err: unknown) => {
        if (currentFetch !== fetchCountRef.current) return;
        setError(err instanceof Error ? err.message : "Unknown error");
        setEntries([]);
        setTotal(0);
        setOffset(0);
      })
      .finally(() => {
        if (currentFetch === fetchCountRef.current) {
          setEntriesLoading(false);
        }
      });
  }, [selectedFormat, statusFilter, debouncedSearch, ownedOnly]);

  const handleLoadMore = useCallback(async () => {
    if (loadingMore || !selectedFormat) return;
    setLoadingMore(true);
    try {
      const res = await fetchBanList({
        format: selectedFormat,
        status: statusFilter === "all" ? undefined : statusFilter,
        search: debouncedSearch || undefined,
        limit: PAGE_SIZE,
        offset,
        ownedOnly,
      });
      if (res.data) {
        setEntries((prev) => [...prev, ...res.data!]);
        setTotal(res.meta.total ?? offset + res.data.length);
        setOffset((prev) => prev + res.data!.length);
      }
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, selectedFormat, statusFilter, debouncedSearch, ownedOnly, offset]);

  const hasMore = entries.length < total;
  const notSynced = status?.legalities_count === 0;

  const lastSyncedLabel =
    status?.last_synced_at &&
    t("banlist.lastSynced", {
      date: new Date(status.last_synced_at).toLocaleString(
        i18n.language === "pt-BR" ? "pt-BR" : "en-US",
      ),
    });

  return (
    <div data-testid="page-banlist">
      <Breadcrumb
        items={[
          { label: t("nav.dashboard"), to: "/" },
          { label: t("nav.banlist") },
        ]}
      />
      <h1 className="text-2xl font-bold text-white mb-1">
        {t("banlist.title")}
      </h1>
      {lastSyncedLabel && (
        <p className="text-sm text-slate-400 mb-6">{lastSyncedLabel}</p>
      )}
      {!lastSyncedLabel && <div className="mb-6" />}

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
            onChange={(e) => handleFormatChange(e.target.value)}
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

        {/* Owned only toggle */}
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            &nbsp;
          </label>
          <label
            className={`flex items-center gap-2 text-sm ${
              isAuthenticated
                ? "text-slate-300 cursor-pointer"
                : "text-slate-500 cursor-not-allowed"
            }`}
            title={
              isAuthenticated ? undefined : t("banlist.ownedOnlyLoginHint")
            }
          >
            <input
              type="checkbox"
              data-testid="owned-only-toggle"
              checked={ownedOnly}
              disabled={!isAuthenticated}
              onChange={toggleOwnedOnly}
              className="rounded border-slate-600 bg-slate-800 text-indigo-500 focus:ring-cyan-400 disabled:opacity-50"
            />
            {t("banlist.ownedOnly")}
          </label>
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
      ) : notSynced ? (
        <div
          data-testid="banlist-not-synced"
          className="text-slate-400 text-center py-12"
        >
          {t("banlist.emptyNotSynced")}
        </div>
      ) : entries.length === 0 ? (
        <div
          data-testid="banlist-empty"
          className="text-slate-400 text-center py-12"
        >
          {ownedOnly ? t("banlist.emptyOwned") : t("banlist.no_results")}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {entries.map((entry) => (
              <BanListCard
                key={`${entry.card_id}-${entry.format}-${entry.status}`}
                entry={entry}
                getCardName={getCardName}
                onSelect={() => setSelectedEntry(entry)}
              />
            ))}
          </div>
          {hasMore && (
            <div className="text-center mt-6">
              <button
                data-testid="banlist-load-more"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="inline-flex items-center gap-2 rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors disabled:opacity-50"
              >
                {loadingMore ? t("common.loading") : t("banlist.loadMore")}
              </button>
            </div>
          )}
        </>
      )}

      <BanCardDetailModal
        entry={selectedEntry}
        onClose={() => setSelectedEntry(null)}
      />
    </div>
  );
}

function BanListCard({
  entry,
  getCardName,
  onSelect,
}: {
  entry: BanListEntry;
  getCardName: (
    nameEn: string | null | undefined,
    namePt: string | null | undefined,
    fallback: string,
  ) => string;
  onSelect: () => void;
}) {
  const { t } = useTranslation();
  const displayName = getCardName(entry.name_en, entry.name_pt, t("common.unknownCard"));
  const imageUrl =
    entry.image_url ||
    (entry.set_code && entry.collector_number
      ? scryfallImageUrl(entry.set_code, entry.collector_number)
      : null);

  return (
    <button
      type="button"
      data-testid="banlist-card"
      onClick={onSelect}
      className="text-left bg-slate-800 border border-slate-600 rounded-lg overflow-hidden hover:border-slate-500 transition-colors"
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
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <LegalityBadge status={entry.status} size="sm" />
          {entry.owned && (
            <span
              data-testid="banlist-owned-badge"
              className="inline-flex items-center px-2 py-0.5 rounded border border-cyan-700 bg-cyan-900/30 text-cyan-400 text-xs font-medium"
            >
              {t("banlist.ownedQty", { count: entry.owned_quantity })}
            </span>
          )}
        </div>
        {entry.printings > 1 && (
          <p className="text-xs text-slate-500">
            {t("banlist.printings", { count: entry.printings })}
          </p>
        )}
        {entry.effective_date && (
          <p className="text-xs text-slate-500 mt-1">
            {t("banlist.effective_date")}: {entry.effective_date}
          </p>
        )}
      </div>
    </button>
  );
}
