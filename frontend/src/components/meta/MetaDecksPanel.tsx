/*
 * F173 — Metagame top decks panel.
 *
 * i18n keys used by this folder (all with pt-BR defaultValue; T15 adds them to locales):
 *   metaDecks.format.<commander|standard|pioneer|modern|legacy|pauper|vintage>
 *   metaDecks.formatUnavailable
 *   metaDecks.metaShare          ({{pct}})
 *   metaDecks.deckCount          ({{count}})
 *   metaDecks.pricedPct          ({{pct}})
 *   metaDecks.ownedPct           ({{pct}})
 *   metaDecks.loginCta
 *   metaDecks.missingValue       ({{value}})
 *   metaDecks.noCards
 *   metaDecks.board.<commander|main|side>
 *   metaDecks.emptyTitle
 *   metaDecks.emptyHint
 *   metaDecks.loadMore
 *   metaDecks.sourceFooter       ({{source}}, {{date}})
 * Reused existing keys: common.retry, common.loading
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchMetaDecks, fetchMetaFormats } from "../../api/metaDecks";
import type {
  MetaDeckListResponse,
  MetaDeckSummary,
  MetaFormat,
  MetaFormatInfo,
} from "../../types/metaDecks";
import { EmptyState } from "../EmptyState";
import { ErrorBanner } from "../ErrorBanner";
import { MetaDeckRow } from "./MetaDeckRow";
import { MetaFormatPills } from "./MetaFormatPills";

const PAGE_SIZE = 20;

/** "2026-09-24" → "24/09/2026" (no Date parsing, so no timezone shift). */
function formatIsoDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return y && m && d ? `${d}/${m}/${y}` : iso;
}

interface MetaDecksPanelProps {
  format: MetaFormat;
  onFormatChange: (format: MetaFormat) => void;
}

export function MetaDecksPanel({ format, onFormatChange }: MetaDecksPanelProps) {
  const { t } = useTranslation();
  const [formats, setFormats] = useState<MetaFormatInfo[]>([]);
  const [data, setData] = useState<MetaDeckListResponse | null>(null);
  const [decks, setDecks] = useState<MetaDeckSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchMetaFormats({ signal: controller.signal })
      .then((resp) => {
        if (!controller.signal.aborted && resp.data) setFormats(resp.data.formats);
      })
      .catch(() => {
        // Non-fatal: pills stay enabled when availability is unknown.
      });
    return () => controller.abort();
  }, []);

  const loadDecks = useCallback(
    async (offset: number, append: boolean) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      setError(null);
      try {
        const resp = await fetchMetaDecks(
          { format, limit: PAGE_SIZE, offset },
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return;
        if (resp.errors.length > 0) {
          setError(resp.errors[0].message);
        } else if (resp.data) {
          const page = resp.data;
          setData(page);
          setDecks((prev) => (append ? [...prev, ...page.decks] : page.decks));
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : String(err));
      }
      setLoading(false);
    },
    [format],
  );

  useEffect(() => {
    setDecks([]);
    setData(null);
    setExpandedId(null);
    loadDecks(0, false);
  }, [loadDecks]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const hasMore = data !== null && decks.length < data.total;

  return (
    <div data-testid="meta-decks-panel">
      <div className="mb-4">
        <MetaFormatPills value={format} formats={formats} onChange={onFormatChange} />
      </div>

      {error && (
        <ErrorBanner message={error} variant="full" onRetry={() => loadDecks(0, false)} />
      )}

      {loading && decks.length === 0 && !error && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 rounded-lg bg-slate-800 animate-pulse"
              data-testid="meta-decks-skeleton"
            />
          ))}
        </div>
      )}

      {!loading && decks.length === 0 && !error && (
        <div data-testid="meta-decks-empty">
          <EmptyState
            title={t("metaDecks.emptyTitle", {
              defaultValue: "Metagame ainda não coletado para este formato",
            })}
            description={t("metaDecks.emptyHint", {
              defaultValue: "Volte mais tarde ou escolha outro formato.",
            })}
          />
        </div>
      )}

      {decks.length > 0 && (
        <div className="space-y-2" data-testid="meta-decks-list">
          {decks.map((deck) => (
            <MetaDeckRow
              key={deck.id}
              deck={deck}
              expanded={expandedId === deck.id}
              onToggle={() => setExpandedId((cur) => (cur === deck.id ? null : deck.id))}
            />
          ))}

          {hasMore && (
            <div className="text-center pt-4">
              <button
                type="button"
                onClick={() => loadDecks(decks.length, true)}
                disabled={loading}
                className="px-6 py-2 rounded-md text-sm font-medium bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors disabled:opacity-50"
                data-testid="meta-load-more-btn"
              >
                {loading
                  ? t("common.loading")
                  : t("metaDecks.loadMore", { defaultValue: "Carregar mais" })}
              </button>
            </div>
          )}

          {data?.source && data.snapshot_date && (
            <p className="pt-4 text-xs text-slate-500" data-testid="meta-decks-footer">
              {t("metaDecks.sourceFooter", {
                defaultValue: "Fonte: {{source}} · atualizado em {{date}}",
                source: data.source,
                date: formatIsoDate(data.snapshot_date),
              })}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
