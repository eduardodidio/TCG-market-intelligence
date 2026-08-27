import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  confirmAgreement,
  fetchMyTrades,
  respondToInterest,
  type TradeDetail,
} from "../api/marketplace";
import { Breadcrumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { TradeCard } from "../components/TradeCard";

export function MyTrades() {
  const { t } = useTranslation();
  const [trades, setTrades] = useState<TradeDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"buyer" | "seller">("buyer");

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
        const result = await confirmAgreement(id);
        if (result.both_confirmed) {
          await loadTrades();
        } else {
          await loadTrades();
        }
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

  const buyerTrades = trades.filter((t) => t.my_role === "buyer");
  const sellerTrades = trades.filter((t) => t.my_role === "seller");
  const activeTrades = activeTab === "buyer" ? buyerTrades : sellerTrades;

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
          {t("marketplace.asBuyer")} ({buyerTrades.length})
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
          {t("marketplace.asSeller")} ({sellerTrades.length})
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadTrades} />}

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="bg-slate-800 border border-slate-600 rounded-lg p-4 h-24 animate-pulse"
            />
          ))}
        </div>
      )}

      {!loading && activeTrades.length === 0 && (
        <EmptyState
          message={
            activeTab === "buyer"
              ? t("marketplace.noListings")
              : t("marketplace.noListings")
          }
        />
      )}

      {!loading && activeTrades.length > 0 && (
        <div className="space-y-3">
          {activeTrades.map((trade) => (
            <TradeCard
              key={trade.id}
              trade={trade}
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
