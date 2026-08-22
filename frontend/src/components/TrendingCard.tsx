import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useCardName } from "../hooks/useCardName";
import type { TrendingCardEntry } from "../types/api";

interface TrendingCardProps {
  entry: TrendingCardEntry;
}

function formatCurrency(value: number, currency: string): string {
  if (currency === "USD") return `$${value.toFixed(2)}`;
  if (currency === "PILA") return `${value.toFixed(2)} pilas`;
  return `R$${value.toFixed(2)}`;
}

function scoreColor(score: number): string {
  if (score >= 70) return "bg-green-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-red-500";
}

export function TrendingCard({ entry }: TrendingCardProps) {
  const { t } = useTranslation();
  const { getCardName } = useCardName();
  const [imgError, setImgError] = useState(false);

  const isUp = entry.change_pct > 0;
  const arrow = isUp ? "\u2191" : "\u2193";
  const changeColor = isUp ? "text-green-400" : "text-red-400";
  const sign = isUp ? "+" : "";
  const displayName = getCardName(entry.name_en, entry.name_pt);

  return (
    <Link
      to={`/cards/${entry.card_id}`}
      className="flex-shrink-0 w-44 rounded-lg bg-slate-800 border border-slate-700 p-3 hover:ring-2 hover:ring-cyan-400 transition-all"
      data-testid="trending-card"
    >
      {/* Card image */}
      <div className="w-16 h-[90px] mx-auto mb-2 rounded overflow-hidden bg-slate-700">
        {entry.image_url && !imgError ? (
          <img
            src={entry.image_url}
            alt={displayName}
            loading="lazy"
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-500 text-xs">
            {t("common.noImage")}
          </div>
        )}
      </div>

      {/* Card name */}
      <p className="text-sm font-medium text-white truncate" title={displayName}>
        {displayName}
      </p>

      {/* Set code badge */}
      {entry.set_code && (
        <p className="text-xs text-slate-400 uppercase mt-0.5">{entry.set_code}</p>
      )}

      {/* Price change line */}
      <div className={`flex items-center gap-1 mt-1 text-sm font-semibold ${changeColor}`}>
        <span>{arrow}</span>
        <span>{sign}{entry.change_pct.toFixed(1)}%</span>
      </div>
      <p className={`text-xs ${changeColor}`}>
        ({sign}{formatCurrency(entry.change_abs, entry.currency)})
      </p>

      {/* Composite score bar */}
      <div
        className="mt-2 h-1.5 w-full rounded-full bg-slate-700 overflow-hidden"
        title={`${t("trending.compositeScore")}: ${entry.composite_score.toFixed(1)}`}
      >
        <div
          className={`h-full rounded-full ${scoreColor(entry.composite_score)}`}
          style={{ width: `${Math.min(entry.composite_score, 100)}%` }}
          data-testid="score-bar"
        />
      </div>
    </Link>
  );
}
