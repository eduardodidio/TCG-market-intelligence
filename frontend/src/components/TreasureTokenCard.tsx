import { useTranslation } from "react-i18next";

interface TreasureTokenCardProps {
  count: number;
}

export function TreasureTokenCard({ count }: TreasureTokenCardProps) {
  const { t } = useTranslation();

  return (
    <div
      className="w-48 rounded-lg overflow-hidden shadow-2xl border-2 border-amber-500/50"
      data-testid="treasure-token-card"
    >
      <div className="bg-gradient-to-b from-amber-800 via-amber-700 to-amber-900 p-1">
        {/* Card name bar */}
        <div className="bg-amber-100 text-amber-900 px-2 py-0.5 text-xs font-serif rounded-t">
          {t("credits.balance")}
        </div>
        {/* Art box */}
        <div
          className="bg-gradient-to-br from-yellow-400 via-amber-500 to-yellow-600
                      h-28 flex items-center justify-center relative mx-0.5 my-0.5"
        >
          <div className="text-5xl select-none" data-testid="treasure-icon">
            &#x1FA99;
          </div>
          <div
            className="absolute bottom-1 right-1 bg-black/70 text-amber-400
                        rounded-full w-8 h-8 flex items-center justify-center
                        text-sm font-bold border border-amber-500"
            data-testid="treasure-count"
          >
            {count}
          </div>
        </div>
        {/* Type line */}
        <div className="bg-amber-100 text-amber-900 px-2 py-0.5 text-[10px] font-serif mx-0.5">
          Token Artifact — Treasure
        </div>
        {/* Text box */}
        <div className="bg-amber-50 text-amber-900 px-2 py-1 text-[9px] italic mx-0.5 mb-0.5 rounded-b">
          &quot;Tap, Sacrifice this artifact: Add one mana of any color.&quot;
        </div>
      </div>
    </div>
  );
}
