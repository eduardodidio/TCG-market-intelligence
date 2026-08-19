import { Link } from "react-router-dom";
import type { MoverEntry } from "../types/api";
import { formatBRL, formatPercent } from "../utils/format";

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
  const accentClass = type === "gainers" ? "text-green-400" : "text-red-400";
  const changeColorClass =
    type === "gainers" ? "text-green-400" : "text-red-400";

  return (
    <div data-testid={`movers-table-${type}`} className="rounded-xl bg-slate-800">
      <div className="rounded-t-xl bg-slate-700/50 px-6 py-4">
        <h3 className={`text-lg font-semibold ${accentClass}`}>{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400">
              <th scope="col" className="px-6 py-3 font-medium">#</th>
              <th scope="col" className="px-6 py-3 font-medium">Card</th>
              <th scope="col" className="hidden px-6 py-3 font-medium sm:table-cell">
                Start Price
              </th>
              <th scope="col" className="hidden px-6 py-3 font-medium sm:table-cell">
                End Price
              </th>
              <th scope="col" className="px-6 py-3 font-medium text-right">Change</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, index) => (
              <tr
                key={entry.card_id}
                className={`border-b border-slate-700/50 transition-colors hover:bg-slate-700 ${
                  index % 2 === 0 ? "bg-slate-800" : "bg-slate-800/50"
                }`}
              >
                <td className="px-6 py-3 text-slate-400">{index + 1}</td>
                <td className="px-6 py-3">
                  <Link
                    to={`/cards/${entry.card_id}`}
                    className="text-white hover:text-cyan-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
                  >
                    {entry.name_en}
                  </Link>
                  {entry.set_code && (
                    <span className="ml-2 text-xs text-slate-500">
                      {entry.set_code}
                    </span>
                  )}
                </td>
                <td className="hidden px-6 py-3 text-slate-300 sm:table-cell">
                  {formatBRL(entry.price_start)}
                </td>
                <td className="hidden px-6 py-3 text-slate-300 sm:table-cell">
                  {formatBRL(entry.price_end)}
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
