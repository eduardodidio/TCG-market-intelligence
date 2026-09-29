import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  fetchCollectionMovers,
  type CollectionMoverData,
} from "../api/collection";
import { MoversTickerItem } from "./MoversTickerItem";

interface MoverItem {
  card_id: number;
  card_name: string;
  change_pct: number;
  type: "gainer" | "loser";
}

function interleave(
  gainers: CollectionMoverData[],
  losers: CollectionMoverData[],
): MoverItem[] {
  const items: MoverItem[] = [];
  const maxLen = Math.max(gainers.length, losers.length);
  for (let i = 0; i < maxLen; i++) {
    if (i < gainers.length) {
      items.push({
        card_id: gainers[i].card_id,
        card_name: gainers[i].card_name,
        change_pct: gainers[i].change_pct,
        type: "gainer",
      });
    }
    if (i < losers.length) {
      items.push({
        card_id: losers[i].card_id,
        card_name: losers[i].card_name,
        change_pct: losers[i].change_pct,
        type: "loser",
      });
    }
  }
  return items;
}

export function MoversTicker() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [items, setItems] = useState<MoverItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchCollectionMovers(7, 10, true)
      .then((res) => {
        if (!cancelled && res.data) {
          setItems(interleave(res.data.gainers, res.data.losers));
        }
      })
      .catch(() => {
        // silently ignore — ticker is non-critical UI
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading || items.length === 0) return null;

  const duration = Math.max(10, (items.length * 60) / 60);

  const handleClick = (cardId: number) => {
    navigate(`/cards/${cardId}`);
  };

  return (
    <div
      className="w-full bg-slate-800/80 border-b border-slate-700 overflow-hidden"
      role="marquee"
      aria-label={t("movers.tickerAriaLabel")}
      aria-live="off"
      data-testid="movers-ticker"
    >
      <div
        className="animate-ticker flex whitespace-nowrap motion-reduce:animate-none motion-reduce:overflow-x-auto"
        style={
          { "--ticker-duration": `${duration}s` } as React.CSSProperties
        }
      >
        {[...items, ...items].map((item, index) => (
          <MoversTickerItem
            key={`${item.card_id}-${index}`}
            card_id={item.card_id}
            card_name={item.card_name}
            change_pct={item.change_pct}
            type={item.type}
            onClick={handleClick}
            tabIndex={index >= items.length ? -1 : undefined}
          />
        ))}
      </div>
    </div>
  );
}
