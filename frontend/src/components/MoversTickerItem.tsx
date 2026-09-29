interface MoversTickerItemProps {
  card_id: number;
  card_name: string;
  change_pct: number;
  type: "gainer" | "loser";
  onClick: (cardId: number) => void;
  tabIndex?: number;
}

export function MoversTickerItem({
  card_id,
  card_name,
  change_pct,
  type,
  onClick,
  tabIndex,
}: MoversTickerItemProps) {
  const isGainer = type === "gainer";
  const colorClass = isGainer ? "text-emerald-400" : "text-red-400";
  const sign = isGainer ? "+" : "-";
  const arrow = isGainer ? "\u25B2" : "\u25BC";
  const pct = Math.abs(change_pct).toFixed(1);

  return (
    <button
      className="inline-flex items-center gap-1.5 px-4 py-1.5 border-r border-slate-600 cursor-pointer hover:bg-slate-700/50 transition-colors whitespace-nowrap"
      onClick={() => onClick(card_id)}
      tabIndex={tabIndex}
      data-testid="movers-ticker-item"
    >
      <span className="text-slate-200 text-sm truncate max-w-[120px]">
        {card_name}
      </span>
      <span className={`text-sm ${colorClass}`}>
        {arrow} {sign}{pct}%
      </span>
    </button>
  );
}
