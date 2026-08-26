import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCredits } from "../hooks/useCredits";

export function TreasureBalance() {
  const { t } = useTranslation();
  const { balance, bonusEligible, isAdmin, loading, claimBonus } =
    useCredits();
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
      {/* Gold coin/token icon - MTG Treasure Token style */}
      <div
        className="w-8 h-8 rounded-full bg-gradient-to-br from-yellow-400 via-amber-500 to-yellow-600
                    border-2 border-yellow-300 shadow-lg flex items-center justify-center flex-shrink-0"
        data-testid="treasure-icon"
      >
        <span className="text-yellow-900 text-xs font-bold">T</span>
      </div>
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
