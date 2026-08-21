import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { MoverEntry } from "../types/api";
import { formatPercent } from "../utils/format";

interface MoversPreviewProps {
  gainers: MoverEntry[];
  losers: MoverEntry[];
}

function DirectionArrow({ type }: { type: "gainer" | "loser" }) {
  if (type === "gainer") {
    return (
      <svg className="h-3.5 w-3.5 inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
      </svg>
    );
  }
  return (
    <svg className="h-3.5 w-3.5 inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function MoverRow({ entry, type }: { entry: MoverEntry; type: "gainer" | "loser" }) {
  const colorClass = type === "gainer" ? "text-tcg-gain" : "text-tcg-loss";

  return (
    <li className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2 min-w-0">
        <Link
          to={`/cards/${entry.card_id}`}
          className="truncate text-sm text-white hover:text-tcg-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary rounded"
        >
          {entry.name_en}
        </Link>
        {entry.set_code && (
          <span className="shrink-0 rounded-tcg-sm bg-tcg-card-alt px-1.5 py-0.5 text-xs text-tcg-muted">
            {entry.set_code}
          </span>
        )}
      </div>
      <span className={`shrink-0 ml-2 text-sm font-medium ${colorClass}`} data-testid="mover-change">
        <DirectionArrow type={type} />{" "}
        {formatPercent(entry.change_pct)}
      </span>
    </li>
  );
}

export function MoversPreview({ gainers, losers }: MoversPreviewProps) {
  const { t } = useTranslation();
  return (
    <div
      data-testid="movers-preview"
      className="grid gap-6 md:grid-cols-2"
    >
      <div className="rounded-tcg-lg bg-tcg-card border border-tcg-border p-6">
        <h3 className="mb-4 text-lg font-semibold text-tcg-gain">{t("dashboard.topGainers")}</h3>
        <ul className="divide-y divide-tcg-border/50">
          {gainers.map((entry) => (
            <MoverRow key={entry.card_id} entry={entry} type="gainer" />
          ))}
        </ul>
        <Link
          to="/market/movers"
          className="mt-4 inline-block text-sm text-tcg-secondary hover:text-tcg-secondary-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary rounded"
        >
          {t("common.viewAll")}
        </Link>
      </div>
      <div className="rounded-tcg-lg bg-tcg-card border border-tcg-border p-6">
        <h3 className="mb-4 text-lg font-semibold text-tcg-loss">{t("dashboard.topLosers")}</h3>
        <ul className="divide-y divide-tcg-border/50">
          {losers.map((entry) => (
            <MoverRow key={entry.card_id} entry={entry} type="loser" />
          ))}
        </ul>
        <Link
          to="/market/movers"
          className="mt-4 inline-block text-sm text-tcg-secondary hover:text-tcg-secondary-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary rounded"
        >
          {t("common.viewAll")}
        </Link>
      </div>
    </div>
  );
}
