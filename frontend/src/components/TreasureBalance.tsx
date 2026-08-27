import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCredits } from "../hooks/useCredits";
import { useTreasureImage } from "../hooks/useTreasureImage";

export function TreasureBalance() {
  const { t } = useTranslation();
  const { balance, bonusEligible, isAdmin, loading, claimBonus } =
    useCredits();
  const treasureImage = useTreasureImage();
  const [claimed, setClaimed] = useState(false);

  const handleClaim = async () => {
    await claimBonus();
    setClaimed(true);
    setTimeout(() => setClaimed(false), 1500);
  };

  if (loading && balance === null) {
    return (
      <div
        className="flex items-center gap-2 px-6 py-3"
        data-testid="treasure-balance"
      >
        <div className="w-8 h-8 rounded-full bg-slate-700 animate-pulse" />
        <span className="text-sm text-slate-500">...</span>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-2 px-6 py-3"
      data-testid="treasure-balance"
    >
      {/* Treasure Token card image */}
      <img
        src={treasureImage}
        alt={t("credits.balance")}
        className="w-8 h-8 rounded-full object-cover border-2 border-yellow-300 shadow-lg flex-shrink-0"
        data-testid="treasure-icon"
      />
      <div className="flex flex-col min-w-0">
        <div className="flex items-center gap-1.5">
          <span
            className={`font-semibold text-sm transition-colors duration-300 ${
              claimed ? "text-emerald-400" : "text-amber-400"
            }`}
            data-testid="treasure-balance-value"
          >
            {balance ?? "..."}
          </span>
          {isAdmin && (
            <span
              className="text-xs text-cyan-400 font-medium px-1 py-0.5 bg-cyan-400/10 rounded"
              data-testid="admin-badge"
            >
              {t("credits.admin")}
            </span>
          )}
        </div>
        <span className="text-xs text-slate-500 truncate">
          {t("credits.balance")}
        </span>
        {bonusEligible && (
          <button
            onClick={handleClaim}
            className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors text-left mt-0.5"
            data-testid="claim-bonus-button"
          >
            {t("credits.claimBonus")}
          </button>
        )}
      </div>
    </div>
  );
}
