import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { MarketplaceListing } from "../api/marketplace";
import { useCardName } from "../hooks/useCardName";

interface TradeInterestModalProps {
  listing: MarketplaceListing;
  onSubmit: (message: string | undefined) => Promise<void>;
  onCancel: () => void;
}

export function TradeInterestModal({
  listing,
  onSubmit,
  onCancel,
}: TradeInterestModalProps) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const displayName = getCardName(listing.card_name_en, listing.card_name_pt);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(message.trim() || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to express interest");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-testid="trade-interest-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
        <h2 className="text-lg font-bold text-white mb-4">
          {t("marketplace.expressInterest")}
        </h2>

        <div className="mb-4">
          <p className="text-sm text-white font-medium">{displayName}</p>
          <p className="text-xs text-slate-400">
            {listing.set_code.toUpperCase()} #{listing.collector_number}
          </p>
        </div>

        <div className="bg-slate-700/50 rounded-lg p-3 mb-4">
          <p className="text-sm text-amber-400" data-testid="fee-preview">
            {t("marketplace.estimatedFee", { fee: listing.estimated_fee })}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            {t("marketplace.feeCharged", { fee: listing.estimated_fee })}
          </p>
        </div>

        <div className="mb-4">
          <textarea
            data-testid="interest-message"
            className="w-full bg-slate-700 border border-slate-600 rounded-lg p-3 text-sm
              text-white placeholder-slate-400 focus:outline-none focus:ring-2
              focus:ring-cyan-400/50 resize-none"
            rows={3}
            placeholder={t("marketplace.addMessage")}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            maxLength={500}
          />
        </div>

        {error && (
          <p className="text-sm text-red-400 mb-3" data-testid="interest-error">
            {error}
          </p>
        )}

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="flex-1 px-4 py-2 text-sm font-medium text-slate-300
              bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
            data-testid="interest-cancel-btn"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 px-4 py-2 text-sm font-medium text-white
              bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="interest-submit-btn"
          >
            {submitting ? t("common.loading") : t("marketplace.interested")}
          </button>
        </div>
      </div>
    </div>
  );
}
