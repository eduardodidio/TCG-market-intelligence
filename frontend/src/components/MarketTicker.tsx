import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useTickerData } from "../hooks/useTickerData";
import { TickerItem } from "./TickerItem";

export function MarketTicker() {
  const { t } = useTranslation();
  const { items, loading } = useTickerData();
  const navigate = useNavigate();

  if (loading || items.length === 0) return null;

  // Calculate animation duration for consistent speed (~60px/item, ~60px/s)
  const duration = Math.max(10, (items.length * 60) / 60);

  const handleClick = (cardId: number) => {
    navigate(`/cards/${cardId}`);
  };

  return (
    <div
      className="hidden md:block w-full bg-slate-800/80 border-b border-slate-700 overflow-hidden"
      role="marquee"
      aria-label={t("ticker.ariaLabel")}
      aria-live="off"
      data-testid="market-ticker"
    >
      <div
        className="animate-ticker flex whitespace-nowrap motion-reduce:animate-none motion-reduce:overflow-x-auto"
        style={
          { "--ticker-duration": `${duration}s` } as React.CSSProperties
        }
      >
        {[...items, ...items].map((item, index) => (
          <TickerItem
            key={`${item.card_id}-${index}`}
            item={item}
            onClick={handleClick}
            tabIndex={index >= items.length ? -1 : undefined}
          />
        ))}
      </div>
    </div>
  );
}
