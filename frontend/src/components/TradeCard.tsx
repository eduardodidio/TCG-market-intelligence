import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { TradeDetail } from "../api/marketplace";
import { Card3DTilt } from "./Card3DTilt";
import { CardImage } from "./CardImage";
import { scryfallImageUrl, scryfallImageByName } from "../utils/scryfall";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-600/20 text-yellow-400 border-yellow-600/50",
  accepted: "bg-blue-600/20 text-blue-400 border-blue-600/50",
  rejected: "bg-red-600/20 text-red-400 border-red-600/50",
  completed: "bg-green-600/20 text-green-400 border-green-600/50",
  cancelled: "bg-slate-600/20 text-slate-400 border-slate-600/50",
};

interface TradeCardProps {
  trade: TradeDetail;
  compact?: boolean;
  onAccept?: (id: number) => void;
  onReject?: (id: number) => void;
  onConfirm?: (id: number) => void;
}

export function TradeCard({ trade, compact = false, onAccept, onReject, onConfirm }: TradeCardProps) {
  const { t } = useTranslation();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const statusStyle = STATUS_STYLES[trade.status] || STATUS_STYLES.pending;
  const primaryUrl = scryfallImageUrl(trade.set_code, trade.collector_number);
  const fallbackUrl = scryfallImageByName(trade.card_name);

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
    <Card3DTilt foil={false} className="w-full">
      <div
        className="group block bg-slate-800 rounded-lg overflow-hidden border border-slate-600
          hover:border-cyan-400/50 transition-all duration-300 hover:shadow-lg relative"
        data-testid={`trade-card-${trade.id}`}
      >
        <div className="aspect-[5/7] bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center overflow-hidden relative">
          <CardImage src={primaryUrl} fallbackSrc={fallbackUrl} alt={trade.card_name} />

          <span
            className={`absolute top-2 left-2 z-10 text-xs px-2 py-0.5 rounded-full border whitespace-nowrap ${statusStyle}`}
            data-testid={`trade-status-${trade.id}`}
          >
            {t(`tradeFilters.status.${trade.status}`)}
          </span>
        </div>

        <div className="p-3 space-y-1.5">
          <h3 className="text-sm font-semibold text-white truncate" title={trade.card_name}>
            {trade.card_name}
          </h3>

          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{trade.set_code.toUpperCase()} #{trade.collector_number}</span>
            <span>
              {trade.my_role === "buyer" ? t("marketplace.asBuyer") : t("marketplace.asSeller")}
            </span>
          </div>

          {!compact && (
            <p className="text-xs text-amber-400">
              {t("marketplace.estimatedFee", { fee: trade.estimated_fee })}
            </p>
          )}

          {!compact && trade.counterparty_share_code && (
            <p className="text-[10px] text-slate-500">
              {trade.counterparty_share_code.slice(0, 8)}...
            </p>
          )}

          {showCompleted && trade.counterparty_email && (
            <div
              className="bg-green-900/30 border border-green-600/50 rounded-lg p-3"
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

          {trade.status === "accepted" && (
            <p className="text-xs text-blue-400" data-testid={`trade-pending-${trade.id}`}>
              {t("marketplace.pendingConfirmation")}
            </p>
          )}

          {(showAcceptReject || (showConfirm && onConfirm)) && (
            <div className="flex gap-2 pt-1">
              {showAcceptReject && (
                <>
                  <button
                    type="button"
                    onClick={() => handleAction("accept", onAccept)}
                    disabled={actionLoading === "accept"}
                    className="flex-1 px-3 py-1.5 text-xs font-medium bg-green-600 hover:bg-green-500
                      text-white rounded-md transition-colors disabled:opacity-50"
                    data-testid={`accept-btn-${trade.id}`}
                  >
                    {t("marketplace.accept")}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleAction("reject", onReject)}
                    disabled={actionLoading === "reject"}
                    className="flex-1 px-3 py-1.5 text-xs font-medium bg-red-600 hover:bg-red-500
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
                  className="w-full px-3 py-1.5 text-xs font-medium bg-amber-600 hover:bg-amber-500
                    text-white rounded-md transition-colors disabled:opacity-50"
                  data-testid={`confirm-btn-${trade.id}`}
                >
                  {t("marketplace.confirmTrade")}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </Card3DTilt>
  );
}
