import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchMetaDeck } from "../../api/metaDecks";
import type { MetaDeckCard, MetaDeckSummary } from "../../types/metaDecks";
import { formatCurrency } from "../../utils/format";
import { MetaDeckCardList } from "./MetaDeckCardList";

const COLOR_CLASSES: Record<string, string> = {
  W: "bg-amber-100",
  U: "bg-blue-500",
  B: "bg-slate-950 ring-1 ring-slate-500",
  R: "bg-red-500",
  G: "bg-green-500",
};

function ColorPips({ colors }: { colors: string | null }) {
  const pips = (colors ?? "").toUpperCase().split("").filter((c) => c in COLOR_CLASSES);
  if (pips.length === 0) {
    return (
      <span
        className="inline-block h-3 w-3 rounded-full bg-slate-500"
        title="C"
        data-testid="meta-deck-color-C"
      />
    );
  }
  return (
    <span className="inline-flex gap-0.5" data-testid="meta-deck-colors">
      {pips.map((c) => (
        <span
          key={c}
          className={`inline-block h-3 w-3 rounded-full ${COLOR_CLASSES[c]}`}
          title={c}
          data-testid={`meta-deck-color-${c}`}
        />
      ))}
    </span>
  );
}

interface MetaDeckRowProps {
  deck: MetaDeckSummary;
  expanded: boolean;
  onToggle: () => void;
}

export function MetaDeckRow({ deck, expanded, onToggle }: MetaDeckRowProps) {
  const { t } = useTranslation();
  const [cards, setCards] = useState<MetaDeckCard[] | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadDetail = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setDetailLoading(true);
    setDetailError(null);
    try {
      const resp = await fetchMetaDeck(deck.id, { signal: controller.signal });
      if (controller.signal.aborted) return;
      if (resp.errors.length > 0) {
        setDetailError(resp.errors[0].message);
      } else if (resp.data) {
        setCards(resp.data.cards);
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      setDetailError(err instanceof Error ? err.message : String(err));
    }
    setDetailLoading(false);
  }, [deck.id]);

  useEffect(() => {
    // Lazy: the decklist is fetched on first expansion (and re-expansion after an error).
    if (expanded && cards === null) loadDetail();
  }, [expanded, cards, loadDetail]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const title = deck.commander_name ?? deck.archetype;
  const ownedPct = deck.owned_pct;

  return (
    <div
      className="rounded-lg bg-slate-800 border border-slate-600 hover:border-cyan-500/50 transition-all duration-200"
      data-testid={`meta-deck-row-${deck.id}`}
    >
      <div className="flex items-center gap-4 p-4">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={expanded}
          className="flex flex-1 min-w-0 items-center gap-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
          data-testid="meta-deck-toggle"
        >
          <span
            className="text-2xl font-bold text-slate-500 w-10 text-center"
            data-testid="meta-deck-rank"
          >
            #{deck.rank}
          </span>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3
                className="text-base font-semibold text-white truncate"
                data-testid="meta-deck-name"
              >
                {title}
              </h3>
              <ColorPips colors={deck.colors} />
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1">
              {deck.meta_share_pct !== null ? (
                <span data-testid="meta-deck-share">
                  {t("metaDecks.metaShare", {
                    defaultValue: "{{pct}}% do meta",
                    pct: deck.meta_share_pct.toFixed(1),
                  })}
                </span>
              ) : deck.deck_count !== null ? (
                <span data-testid="meta-deck-count">
                  {t("metaDecks.deckCount", {
                    defaultValue: "{{count}} decks",
                    count: deck.deck_count,
                  })}
                </span>
              ) : null}
              {deck.priced_pct !== null && deck.priced_pct < 100 && (
                <span data-testid="meta-deck-priced">
                  {t("metaDecks.pricedPct", {
                    defaultValue: "{{pct}}% das cartas com preço",
                    pct: deck.priced_pct.toFixed(0),
                  })}
                </span>
              )}
            </div>

            {ownedPct !== null ? (
              <div className="mt-2 flex items-center gap-2" data-testid="meta-owned">
                <div className="h-1.5 w-32 rounded-full bg-slate-700 overflow-hidden">
                  <div
                    className="h-full bg-cyan-500"
                    style={{ width: `${Math.max(0, Math.min(100, ownedPct))}%` }}
                    data-testid="meta-owned-bar"
                  />
                </div>
                <span className="text-xs text-slate-300" data-testid="meta-owned-pct">
                  {t("metaDecks.ownedPct", {
                    defaultValue: "Você possui {{pct}}%",
                    pct: ownedPct.toFixed(0),
                  })}
                </span>
              </div>
            ) : (
              <p className="mt-2 text-xs text-cyan-400" data-testid="meta-owned-login-cta">
                {t("metaDecks.loginCta", {
                  defaultValue: "Entre para ver quanto você já tem",
                })}
              </p>
            )}
          </div>

          <div className="text-right min-w-[110px]">
            <p className="text-lg font-bold text-white" data-testid="meta-deck-value">
              {deck.total_value_brl !== null ? formatCurrency(deck.total_value_brl) : "—"}
            </p>
            {ownedPct !== null && deck.missing_value_brl !== null && (
              <p className="text-xs text-amber-400" data-testid="meta-deck-missing">
                {t("metaDecks.missingValue", {
                  defaultValue: "Faltam {{value}}",
                  value: formatCurrency(deck.missing_value_brl),
                })}
              </p>
            )}
          </div>
        </button>

        <a
          href={deck.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-xs text-slate-400 hover:text-cyan-400 underline"
          data-testid="meta-deck-source-link"
        >
          {deck.source}
        </a>
      </div>

      {expanded && (
        <div className="border-t border-slate-700 p-4" data-testid="meta-deck-detail">
          {detailLoading && (
            <div className="space-y-2" data-testid="meta-deck-detail-loading">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-4 rounded bg-slate-700 animate-pulse" />
              ))}
            </div>
          )}
          {!detailLoading && detailError && (
            <div
              className="flex items-center gap-3 text-sm text-red-400"
              role="alert"
              data-testid="meta-deck-detail-error"
            >
              <span>{detailError}</span>
              <button
                type="button"
                onClick={loadDetail}
                className="rounded bg-red-700 px-2 py-0.5 text-xs text-white hover:bg-red-600"
                data-testid="meta-deck-detail-retry"
              >
                {t("common.retry")}
              </button>
            </div>
          )}
          {!detailLoading && !detailError && cards !== null && (
            <MetaDeckCardList cards={cards} />
          )}
        </div>
      )}
    </div>
  );
}
