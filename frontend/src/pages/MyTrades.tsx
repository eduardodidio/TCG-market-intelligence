import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import {
  confirmAgreement,
  fetchMyTrades,
  respondToInterest,
  type TradeDetail,
} from "../api/marketplace";
import { Breadcrumb } from "../components/Breadcrumb";
import { CardFilterBar } from "../components/CardFilterBar";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { FilterChips } from "../components/FilterChips";
import { SkeletonCard } from "../components/Skeleton";
import { TradeCard } from "../components/TradeCard";
import { useCardListFilters } from "../hooks/useCardListFilters";
import { useGridSize } from "../hooks/useGridSize";
import { buildSetOptions, filterCardList, sortCardList } from "../utils/cardListFilter";
import { GRID_SIZE_CONFIG } from "../utils/constants";
import { MY_TRADES_SORT_OPTIONS } from "../utils/tradeSortOptions";

const STATUS_OPTIONS = ["pending", "accepted", "completed", "rejected", "cancelled"];

const TRADE_LIST_ACCESSORS = {
  name: (t: TradeDetail) => t.card_name,
  setCode: (t: TradeDetail) => t.set_code,
  number: (t: TradeDetail) => t.collector_number,
  date: (t: TradeDetail) => t.created_at,
  status: (t: TradeDetail) => t.status,
};

export function MyTrades() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [trades, setTrades] = useState<TradeDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const { gridSize, setGridSize } = useGridSize();

  const tabParam = searchParams.get("tab");
  const activeTab: "buyer" | "seller" = tabParam === "seller" ? "seller" : "buyer";

  const setActiveTab = useCallback(
    (tab: "buyer" | "seller") => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (tab === "buyer") {
            next.delete("tab");
          } else {
            next.set("tab", tab);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const {
    search,
    setSearch,
    debouncedSearch,
    selectedSet,
    setSelectedSet,
    sortValue,
    sortBy,
    sortDir,
    setSort,
  } = useCardListFilters({ defaultSortBy: "date", defaultSortDir: "desc" });

  const loadTrades = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetchMyTrades();
      setTrades(resp.trades);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trades");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTrades();
  }, [loadTrades]);

  const handleAccept = useCallback(
    async (id: number) => {
      try {
        await respondToInterest(id, "accept");
        await loadTrades();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to accept");
      }
    },
    [loadTrades],
  );

  const handleReject = useCallback(
    async (id: number) => {
      try {
        await respondToInterest(id, "reject");
        await loadTrades();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to reject");
      }
    },
    [loadTrades],
  );

  const handleConfirm = useCallback(
    async (id: number) => {
      try {
        await confirmAgreement(id);
        await loadTrades();
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to confirm";
        if (msg.includes("INSUFFICIENT_CREDITS")) {
          setError(t("marketplace.insufficientForTrade"));
        } else {
          setError(msg);
        }
      }
    },
    [loadTrades, t],
  );

  const buyerTrades = useMemo(() => trades.filter((tr) => tr.my_role === "buyer"), [trades]);
  const sellerTrades = useMemo(() => trades.filter((tr) => tr.my_role === "seller"), [trades]);
  const roleTrades = activeTab === "buyer" ? buyerTrades : sellerTrades;

  const setOptions = useMemo(() => buildSetOptions(roleTrades, TRADE_LIST_ACCESSORS), [roleTrades]);

  const filteredTrades = useMemo(() => {
    const filtered = filterCardList(
      roleTrades,
      { search: debouncedSearch, set: selectedSet, status: statusFilter },
      TRADE_LIST_ACCESSORS,
    );
    return sortCardList(filtered, sortBy, sortDir, TRADE_LIST_ACCESSORS);
  }, [roleTrades, debouncedSearch, selectedSet, statusFilter, sortBy, sortDir]);

  const filteredBuyerCount = useMemo(
    () => filterCardList(buyerTrades, { search: debouncedSearch, set: selectedSet, status: statusFilter }, TRADE_LIST_ACCESSORS).length,
    [buyerTrades, debouncedSearch, selectedSet, statusFilter],
  );
  const filteredSellerCount = useMemo(
    () => filterCardList(sellerTrades, { search: debouncedSearch, set: selectedSet, status: statusFilter }, TRADE_LIST_ACCESSORS).length,
    [sellerTrades, debouncedSearch, selectedSet, statusFilter],
  );

  const isFiltered = Boolean(debouncedSearch || selectedSet || statusFilter);
  const gridConfig = GRID_SIZE_CONFIG[gridSize];

  return (
    <div data-testid="page-my-trades">
      <Breadcrumb
        items={[
          { label: t("marketplace.title"), to: "/marketplace" },
          { label: t("marketplace.myTrades") },
        ]}
      />

      <h2 className="text-2xl font-bold text-white mb-6">
        {t("marketplace.myTrades")}
      </h2>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-800 rounded-lg p-1 w-fit" data-testid="trade-tabs">
        <button
          type="button"
          onClick={() => setActiveTab("buyer")}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === "buyer"
              ? "bg-cyan-600 text-white"
              : "text-slate-400 hover:text-white"
          }`}
          data-testid="tab-buyer"
        >
          {t("marketplace.asBuyer")} ({filteredBuyerCount})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("seller")}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === "seller"
              ? "bg-cyan-600 text-white"
              : "text-slate-400 hover:text-white"
          }`}
          data-testid="tab-seller"
        >
          {t("marketplace.asSeller")} ({filteredSellerCount})
        </button>
      </div>

      <CardFilterBar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder={t("tradeFilters.searchPlaceholder")}
        sortOptions={MY_TRADES_SORT_OPTIONS}
        sortValue={sortValue}
        onSortChange={setSort}
        setOptions={setOptions}
        selectedSet={selectedSet}
        onSetSelect={setSelectedSet}
        gridSize={gridSize}
        onGridSizeChange={setGridSize}
      >
        <FilterChips
          options={STATUS_OPTIONS.map((s) => ({ label: t(`tradeFilters.status.${s}`), value: s }))}
          selected={statusFilter}
          onSelect={setStatusFilter}
        />
      </CardFilterBar>

      {error && <ErrorBanner message={error} onRetry={loadTrades} />}

      {loading && (
        <div className={`grid ${gridConfig.gridClasses}`}>
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!loading && filteredTrades.length === 0 && (
        <EmptyState
          message={
            isFiltered
              ? t("tradeFilters.noResults")
              : activeTab === "buyer"
                ? t("tradeFilters.noTradesBuyer")
                : t("tradeFilters.noTradesSeller")
          }
        />
      )}

      {!loading && filteredTrades.length > 0 && (
        <div className={`grid ${gridConfig.gridClasses}`}>
          {filteredTrades.map((trade) => (
            <TradeCard
              key={trade.id}
              trade={trade}
              compact={gridConfig.compact}
              onAccept={handleAccept}
              onReject={handleReject}
              onConfirm={handleConfirm}
            />
          ))}
        </div>
      )}
    </div>
  );
}
