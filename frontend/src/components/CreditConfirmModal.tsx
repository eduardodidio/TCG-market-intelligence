import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useTreasureImage } from "../hooks/useTreasureImage";

export interface CreditConfirmModalProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  cost: number;
  balance: number;
  actionLabel: string;
  isAdmin?: boolean;
  cardCount?: number;
  skippedCount?: number;
  bonusEligible?: boolean;
  onClaimBonus?: () => Promise<void>;
  children?: React.ReactNode;
}

export function CreditConfirmModal({
  isOpen,
  onConfirm,
  onCancel,
  cost,
  balance,
  actionLabel,
  isAdmin,
  cardCount,
  skippedCount,
  bonusEligible,
  onClaimBonus,
  children,
}: CreditConfirmModalProps) {
  const { t } = useTranslation();
  const treasureImage = useTreasureImage();
  const [claimedFlash, setClaimedFlash] = useState(false);

  if (!isOpen) return null;

  const insufficient = balance < cost;
  const balanceAfter = balance - cost;

  const handleClaimBonus = async () => {
    if (!onClaimBonus) return;
    await onClaimBonus();
    setClaimedFlash(true);
    setTimeout(() => setClaimedFlash(false), 1500);
  };

  return (
    <div
      data-testid="credit-confirm-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
        {/* Title */}
        <h2
          className="text-lg font-bold text-white text-center mb-4"
          data-testid="modal-title"
        >
          {t("credits.confirmTitle")}
        </h2>

        {/* Treasure Token Card */}
        <div className="flex justify-center mb-4">
          <div className="relative w-32" data-testid="treasure-token-card">
            <img
              src={treasureImage}
              alt={t("credits.balance")}
              className="w-full rounded-lg object-cover shadow-lg"
              data-testid="treasure-image"
            />
            <div
              className="absolute bottom-1 right-1 bg-black/70 text-amber-400
                          rounded-full w-8 h-8 flex items-center justify-center
                          text-sm font-bold border border-amber-500"
              data-testid="treasure-count"
            >
              {balance}
            </div>
          </div>
        </div>

        {/* Cost info */}
        <div className="space-y-2 mb-6 text-center">
          <p className="text-sm text-slate-300" data-testid="cost-text">
            {t("credits.confirmCost", { cost })}
          </p>
          <p className="text-sm text-slate-400" data-testid="balance-text">
            {t("credits.confirmBalance", { balance })}
          </p>
          {!insufficient && (
            <p
              className="text-sm text-slate-400"
              data-testid="balance-after-text"
            >
              {t("credits.balanceAfter", { balance: balanceAfter })}
            </p>
          )}
          {insufficient && (
            <p
              className="text-sm text-red-400 font-medium"
              data-testid="insufficient-text"
            >
              {t("credits.insufficient")}
            </p>
          )}
          {insufficient && bonusEligible && onClaimBonus && (
            <div className="flex items-center justify-center gap-2" data-testid="claim-bonus-section">
              <button
                type="button"
                data-testid="modal-claim-bonus-btn"
                onClick={handleClaimBonus}
                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3 py-1 rounded-md transition-colors"
              >
                {t("credits.claimBonusModal")}
              </button>
              {claimedFlash && (
                <span
                  className="text-xs text-emerald-400 font-medium"
                  data-testid="claimed-flash"
                >
                  Claimed!
                </span>
              )}
            </div>
          )}
          {insufficient && (
            <p
              className="text-xs text-slate-400 mt-2"
              data-testid="earn-info-text"
            >
              {t("credits.earnInfo")}
            </p>
          )}
        </div>

        {/* Card count and skipped info */}
        {cardCount != null && (
          <p
            className="text-sm text-cyan-400 font-medium text-center mb-1"
            data-testid="card-count-text"
          >
            {t("collection.cardsToScan", { count: cardCount })}
          </p>
        )}
        {skippedCount != null && skippedCount > 0 && (
          <p
            className="text-xs text-slate-400 text-center mb-2"
            data-testid="skipped-count-text"
          >
            {t("collection.skippedCards", { count: skippedCount })}
          </p>
        )}

        {/* Extra controls (e.g. max_age_days selector) */}
        {children && <div className="mb-4">{children}</div>}

        {/* Action label */}
        <p className="text-xs text-slate-500 text-center mb-4">
          {actionLabel}
        </p>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            type="button"
            data-testid="modal-cancel-btn"
            onClick={onCancel}
            className="flex-1 px-4 py-2 text-sm font-medium text-slate-300
              bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {t("credits.cancel")}
          </button>
          <button
            type="button"
            data-testid="modal-confirm-btn"
            onClick={onConfirm}
            disabled={insufficient}
            className="flex-1 px-4 py-2 text-sm font-medium text-white
              bg-amber-600 hover:bg-amber-500 rounded-lg transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {t("credits.spend", { cost })}
          </button>
        </div>
      </div>
    </div>
  );
}
