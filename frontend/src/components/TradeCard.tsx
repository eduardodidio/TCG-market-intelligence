import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { TradeDetail } from "../api/marketplace";
import { scryfallImageUrl } from "../utils/scryfall";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-600/20 text-yellow-400 border-yellow-600/50",
  accepted: "bg-blue-600/20 text-blue-400 border-blue-600/50",
  rejected: "bg-red-600/20 text-red-400 border-red-600/50",
  completed: "bg-green-600/20 text-green-400 border-green-600/50",
  cancelled: "bg-slate-600/20 text-slate-400 border-slate-600/50",
};

interface TradeCardProps {
  trade: TradeDetail;
  onAccept?: (id: number) => void;
  onReject?: (id: number) => void;
  onConfirm?: (id: number) => void;
}

export function TradeCard({ trade, onAccept, onReject, onConfirm }: TradeCardProps) {
  const { t } = useTranslation();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const statusStyle = STATUS_STYLES[trade.status] || STATUS_STYLES.pending;
  const imgUrl = scryfallImageUrl(trade.set_code, trade.collector_number, "small");

  const handleAction = async (action: string, handler?: (id: number) => void) => {
    if (!handler) return;
    setActionLoading(action);
    try {
      handler(trade.id);
    } finally {
      setActionLoading(null);
    }
  };

  const isSeller = trade.my_role === "seller";
  const showAcceptReject = isSeller && trade.status === "pending";
  const showConfirm = trade.status === "accepted";
  const showCompleted = trade.status === "completed";

  return (
    <div
      className="bg-slate-800 border border-slate-600 rounded-lg p-4 flex gap-4"
      data-testid={`trade-card-${trade.id}`}
    >
      {/* Card thumbnail */}
      <div className="w-16 h-22 flex-shrink-0">
        <img
          src={imgUrl}
          alt={trade.card_name}
          className="w-full h-full object-cover rounded"
          loading="lazy"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      </div>

      {/* Trade info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className="text-sm font-semibold text-white truncate">
            {trade.card_name}
          </h3>
          <span
            className={`text-xs px-2 py-0.5 rounded-full border whitespace-nowrap ${statusStyle}`}
            data-testid={`trade-status-${trade.id}`}
          >
            {trade.status}
          </span>
        </div>

        <p className="text-xs text-slate-400 mb-1">
          {trade.set_code.toUpperCase()} #{trade.collector_number}
        </p>

        <div className="flex items-center gap-2 text-xs mb-2">
          <span className="text-slate-400">
            {trade.my_role === "buyer" ? t("marketplace.asBuyer") : t("marketplace.asSeller")}
          </span>
          <span className="text-amber-400">
            {t("marketplace.estimatedFee", { fee: trade.estimated_fee })}
          </span>
        </div>

        {trade.counterparty_share_code && (
          <p className="text-[10px] text-slate-500 mb-2">
            {trade.counterparty_share_code.slice(0, 8)}...
          </p>
        )}

        {/* Completed — show email */}
        {showCompleted && trade.counterparty_email && (
          <div
            className="bg-green-900/30 border border-green-600/50 rounded-lg p-3 mb-2"
            data-testid={`trade-completed-${trade.id}`}
          >
            <p className="text-sm font-medium text-green-400">
              {t("marketplace.tradeCompleted")}
            </p>
            <p className="text-sm text-slate-300 mt-1">
              {t("marketplace.contactEmail", { email: trade.counterparty_email })}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              {t("marketplace.feeCharged", { fee: trade.estimated_fee })}
            </p>
          </div>
        )}

        {/* Pending confirmation message */}
        {trade.status === "accepted" && (
          <p className="text-xs text-blue-400 mb-2" data-testid={`trade-pending-${trade.id}`}>
            {t("marketplace.pendingConfirmation")}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex gap-2">
          {showAcceptReject && (
            <>
              <button
                type="button"
                onClick={() => handleAction("accept", onAccept)}
                disabled={actionLoading === "accept"}
                className="px-3 py-1 text-xs font-medium bg-green-600 hover:bg-green-500
                  text-white rounded-md transition-colors disabled:opacity-50"
                data-testid={`accept-btn-${trade.id}`}
              >
                {t("marketplace.accept")}
              </button>
              <button
                type="button"
                onClick={() => handleAction("reject", onReject)}
                disabled={actionLoading === "reject"}
                className="px-3 py-1 text-xs font-medium bg-red-600 hover:bg-red-500
                  text-white rounded-md transition-colors disabled:opacity-50"
                data-testid={`reject-btn-${trade.id}`}
              >
                {t("marketplace.reject")}
              </button>
            </>
          )}

          {showConfirm && onConfirm && (
            <button
              type="button"
              onClick={() => handleAction("confirm", onConfirm)}
              disabled={actionLoading === "confirm"}
              className="px-3 py-1 text-xs font-medium bg-amber-600 hover:bg-amber-500
                text-white rounded-md transition-colors disabled:opacity-50"
              data-testid={`confirm-btn-${trade.id}`}
            >
              {t("marketplace.confirmTrade")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
