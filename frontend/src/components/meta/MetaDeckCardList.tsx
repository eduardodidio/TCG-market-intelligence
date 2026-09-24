import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { MetaDeckCard } from "../../types/metaDecks";
import { formatCurrency } from "../../utils/format";

const BOARD_ORDER = ["commander", "main", "side"] as const;

const BOARD_DEFAULT_LABELS: Record<string, string> = {
  commander: "Comandante",
  main: "Main deck",
  side: "Sideboard",
};

interface MetaDeckCardListProps {
  cards: MetaDeckCard[];
}

function groupByBoard(cards: MetaDeckCard[]): [string, MetaDeckCard[]][] {
  const groups = new Map<string, MetaDeckCard[]>();
  for (const card of cards) {
    const list = groups.get(card.board) ?? [];
    list.push(card);
    groups.set(card.board, list);
  }
  const rank = (b: string) => {
    const idx = (BOARD_ORDER as readonly string[]).indexOf(b);
    return idx === -1 ? BOARD_ORDER.length : idx;
  };
  return [...groups.entries()].sort((a, b) => rank(a[0]) - rank(b[0]));
}

export function MetaDeckCardList({ cards }: MetaDeckCardListProps) {
  const { t } = useTranslation();

  if (cards.length === 0) {
    return (
      <p className="text-sm text-slate-400" data-testid="meta-card-list-empty">
        {t("metaDecks.noCards", { defaultValue: "Decklist indisponível." })}
      </p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2" data-testid="meta-card-list">
      {groupByBoard(cards).map(([board, boardCards]) => {
        const count = boardCards.reduce((sum, c) => sum + c.quantity, 0);
        return (
          <section key={board} data-testid={`meta-board-${board}`}>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">
              {t(`metaDecks.board.${board}`, {
                defaultValue: BOARD_DEFAULT_LABELS[board] ?? board,
              })}{" "}
              <span className="text-slate-500">({count})</span>
            </h4>
            <ul className="divide-y divide-slate-700/60">
              {boardCards.map((card) => {
                const owned = card.owned_qty;
                const fullyOwned = owned !== null && owned >= card.quantity;
                return (
                  <li
                    key={`${board}-${card.name}`}
                    className="flex items-center gap-2 py-1 text-sm"
                    data-testid="meta-card-row"
                  >
                    <span className="w-6 text-right text-slate-400">{card.quantity}</span>
                    <span className="flex-1 min-w-0 truncate text-white">
                      {card.card_id !== null ? (
                        <Link
                          to={`/cards/${card.card_id}`}
                          className="hover:text-cyan-400"
                          data-testid="meta-card-link"
                        >
                          {card.name}
                        </Link>
                      ) : (
                        card.name
                      )}
                    </span>
                    {owned !== null && (
                      <span
                        className={`text-xs ${fullyOwned ? "text-green-400" : "text-slate-400"}`}
                        data-testid="meta-card-owned"
                      >
                        {fullyOwned ? "✓" : `${owned}/${card.quantity}`}
                      </span>
                    )}
                    <span
                      className="w-24 text-right text-slate-300"
                      data-testid="meta-card-price"
                    >
                      {card.price_brl !== null ? formatCurrency(card.price_brl) : "—"}
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
