import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { MoverEntry } from "../types/api";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency, formatPercent } from "../utils/format";

interface MoversTableProps {
  entries: MoverEntry[];
  title: string;
  type: "gainers" | "losers";
}

function DirectionArrow({ type }: { type: "gainers" | "losers" }) {
  if (type === "gainers") {
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

export function MoversTable({ entries, title, type }: MoversTableProps) {
  const { t } = useTranslation();
  const { currency } = useCurrency();
  const accentClass = type === "gainers" ? "text-tcg-gain" : "text-tcg-loss";
  const changeColorClass =
    type === "gainers" ? "text-tcg-gain" : "text-tcg-loss";

  return (
    <div data-testid={`movers-table-${type}`} className="rounded-tcg-lg bg-tcg-card border border-tcg-border">
      <div className="rounded-t-tcg-lg bg-tcg-card-alt/50 px-6 py-4">
        <h3 className={`text-lg font-semibold ${accentClass}`}>{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-tcg-border text-tcg-muted">
              <th scope="col" className="px-6 py-3 font-medium">{t("market.columnRank")}</th>
              <th scope="col" className="px-6 py-3 font-medium">{t("market.columnCard")}</th>
              <th scope="col" className="hidden px-6 py-3 font-medium sm:table-cell">
                {t("market.columnStartPrice")}
              </th>
              <th scope="col" className="hidden px-6 py-3 font-medium sm:table-cell">
                {t("market.columnEndPrice")}
              </th>
              <th scope="col" className="px-6 py-3 font-medium text-right">{t("market.columnChange")}</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, index) => (
              <tr
                key={entry.card_id}
                className={`border-b border-tcg-border/50 transition-colors hover:bg-tcg-card-alt ${
                  index % 2 === 0 ? "bg-tcg-card" : "bg-tcg-card/50"
                }`}
              >
                <td className="px-6 py-3 text-tcg-muted">{index + 1}</td>
                <td className="px-6 py-3">
                  <Link
                    to={`/cards/${entry.card_id}`}
                    className="text-white hover:text-tcg-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary rounded"
                  >
                    {entry.name_en}
                  </Link>
                  {entry.set_code && (
                    <span className="ml-2 text-xs text-tcg-dimmed">
                      {entry.set_code}
                    </span>
                  )}
                </td>
                <td className="hidden px-6 py-3 text-tcg-muted sm:table-cell">
                  {formatCurrency(entry.price_start, currency)}
                </td>
                <td className="hidden px-6 py-3 text-tcg-muted sm:table-cell">
                  {formatCurrency(entry.price_end, currency)}
                </td>
                <td
                  className={`px-6 py-3 text-right font-bold ${changeColorClass}`}
                  data-testid="mover-change"
                >
                  <DirectionArrow type={type} />{" "}
                  {formatPercent(entry.change_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
