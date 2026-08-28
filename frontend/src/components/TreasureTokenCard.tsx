import { useTranslation } from "react-i18next";
import { useTreasureImage } from "../hooks/useTreasureImage";

interface TreasureTokenCardProps {
  count: number;
}

export function TreasureTokenCard({ count }: TreasureTokenCardProps) {
  const { t } = useTranslation();
  const treasureImage = useTreasureImage();

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
        <div className="relative mx-0.5 my-0.5 bg-amber-950">
          <img
            src={treasureImage}
            alt={t("credits.balance")}
            className="w-full h-36 object-cover object-center"
            data-testid="treasure-image"
          />
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
          {t("credits.tokenTypeLine")}
        </div>
        {/* Text box */}
        <div className="bg-amber-50 text-amber-900 px-2 py-1 text-[9px] italic mx-0.5 mb-0.5 rounded-b">
          {t("credits.tokenRulesText")}
        </div>
      </div>
    </div>
  );
}
