import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { saveDeckSuggestion } from "../../api/deckSuggestions";
import type {
  DeckSuggestion,
  SuggestedCard,
} from "../../types/deckSuggestions";
import { formatBRL } from "../../utils/format";

export interface SuggestionResultViewProps {
  suggestion: DeckSuggestion;
  onSaved?: (deckId: number) => void;
}

/** BRL price, or an em dash when unknown (prices are stored in BRL). */
export function formatSuggestionPrice(value: number | null | undefined): string {
  return value == null ? "—" : formatBRL(value);
}

export function getSuggestedCardImageUrl(card: SuggestedCard): string | null {
  if (card.image_uri) return card.image_uri;
  if (card.set_code && card.collector_number) {
    return `https://api.scryfall.com/cards/${card.set_code}/${card.collector_number}?format=image&version=small`;
  }
  return null;
}

interface IndexedCard {
  card: SuggestedCard;
  index: number;
}

/**
 * Groups cards by category in a stable order: "Commander" first, then the
 * other categories alphabetically, "Land" last. Each card keeps its original
 * index (used for the `suggestion-card-{i}` testid).
 */
export function groupSuggestedCards(
  cards: SuggestedCard[],
): Array<{ category: string; items: IndexedCard[] }> {
  const groups = new Map<string, IndexedCard[]>();
  cards.forEach((card, index) => {
    const category = card.category?.trim() || "Other";
    const list = groups.get(category);
    if (list) list.push({ card, index });
    else groups.set(category, [{ card, index }]);
  });
  const rank = (c: string) => {
    const lower = c.toLowerCase();
    if (lower === "commander") return 0;
    if (lower === "land" || lower === "lands") return 2;
    return 1;
  };
  return [...groups.entries()]
    .sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b))
    .map(([category, items]) => ({ category, items }));
}

export function SuggestionResultView({
  suggestion,
  onSaved,
}: SuggestionResultViewProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const result = suggestion.result ?? null;
  const [deckName, setDeckName] = useState(result?.deck_name ?? "");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (suggestion.status === "pending" || suggestion.status === "processing") {
    return (
      <div
        className="rounded-lg border border-amber-600/40 bg-amber-900/20 p-4 text-sm text-amber-200"
        data-testid="suggestion-result-pending"
      >
        {suggestion.status === "processing"
          ? t("deckSuggest.result.processing", {
              defaultValue: "Processando – o resultado aparecerá em breve.",
            })
          : t("deckSuggest.result.pending", {
              defaultValue: "Na fila – será gerado na próxima execução diária.",
            })}
      </div>
    );
  }

  if (suggestion.status === "failed" || !result) {
    return (
      <div
        className="rounded-lg border border-red-600/40 bg-red-900/20 p-4 text-sm text-red-200"
        data-testid="suggestion-result-failed"
      >
        <p className="font-medium mb-1">
          {t("deckSuggest.result.failed", {
            defaultValue: "Não foi possível gerar a sugestão.",
          })}
        </p>
        {suggestion.error_message && <p>{suggestion.error_message}</p>}
      </div>
    );
  }

  const summary = result.summary;
  const groups = groupSuggestedCards(result.cards);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const name = deckName.trim() || result.deck_name;
      const resp = await saveDeckSuggestion(suggestion.id, name);
      if (resp.errors && resp.errors.length > 0) {
        setSaveError(resp.errors[0].message);
        return;
      }
      const deckId = resp.data?.deck_id;
      if (deckId == null) {
        setSaveError(
          t("deckSuggest.result.saveFailed", {
            defaultValue: "Não foi possível salvar o deck.",
          }),
        );
        return;
      }
      onSaved?.(deckId);
      navigate(`/decks/${deckId}`);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const tiles: Array<{ key: string; label: string; value: string }> = [
    {
      key: "total",
      label: t("deckSuggest.result.totalCards", { defaultValue: "Total de cartas" }),
      value: String(summary.total_cards),
    },
    {
      key: "owned",
      label: t("deckSuggest.result.ownedCards", { defaultValue: "Na coleção" }),
      value: String(summary.owned_cards),
    },
    {
      key: "missing",
      label: t("deckSuggest.result.missingCards", { defaultValue: "Faltando" }),
      value: String(summary.missing_cards),
    },
    {
      key: "cost",
      label: t("deckSuggest.result.missingCost", {
        defaultValue: "Custo para completar",
      }),
      value: formatSuggestionPrice(summary.missing_cost_brl),
    },
  ];

  return (
    <div className="space-y-4" data-testid="suggestion-result">
      <div>
        <h3 className="text-lg font-semibold text-white">{result.deck_name}</h3>
        {result.commander && (
          <p className="text-sm text-slate-400" data-testid="suggestion-commander">
            {t("deckSuggest.result.commander", { defaultValue: "Comandante" })}:{" "}
            <span className="text-slate-200">{result.commander.name_en}</span>
          </p>
        )}
        <p className="mt-2 text-sm text-slate-300 whitespace-pre-line" data-testid="suggestion-strategy">
          {result.strategy}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2" data-testid="suggestion-summary">
        {tiles.map((tile) => (
          <div
            key={tile.key}
            className="rounded-lg bg-slate-800 p-3"
            data-testid={`suggestion-summary-${tile.key}`}
          >
            <p className="text-xs text-slate-400">{tile.label}</p>
            <p className="text-lg font-bold text-white">{tile.value}</p>
          </div>
        ))}
      </div>

      {result.warnings.length > 0 && (
        <ul
          className="rounded-lg border border-amber-600/40 bg-amber-900/20 p-3 text-xs text-amber-200 list-disc list-inside"
          data-testid="suggestion-warnings"
        >
          {result.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}

      <div className="space-y-3">
        {groups.map((group) => (
          <section key={group.category}>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">
              {group.category} ({group.items.reduce((n, it) => n + it.card.quantity, 0)})
            </h4>
            <ul className="divide-y divide-slate-700/50 rounded-lg bg-slate-800/50">
              {group.items.map(({ card, index }) => {
                const imgUrl = getSuggestedCardImageUrl(card);
                return (
                  <li
                    key={`${card.card_id ?? card.name_en}-${index}`}
                    className="flex items-center gap-2 px-2 py-1.5 text-sm"
                    data-testid={`suggestion-card-${index}`}
                    title={card.reason ?? undefined}
                  >
                    <span className="w-6 text-right text-slate-400">{card.quantity}x</span>
                    {imgUrl ? (
                      <img
                        src={imgUrl}
                        alt=""
                        className="h-8 w-6 rounded object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <span className="h-8 w-6 rounded bg-slate-700" />
                    )}
                    <span className="flex-1 truncate text-slate-100">{card.name_en}</span>
                    <span className="hidden sm:inline rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-300">
                      {card.category}
                    </span>
                    {card.is_owned ? (
                      <span className="rounded bg-green-700/40 px-1.5 py-0.5 text-xs text-green-300">
                        {t("deckSuggest.result.owned", { defaultValue: "Na coleção" })}
                      </span>
                    ) : (
                      <span className="rounded bg-red-900/40 px-1.5 py-0.5 text-xs text-red-300">
                        {t("deckSuggest.result.missing", { defaultValue: "Falta" })}{" "}
                        {formatSuggestionPrice(card.missing_cost ?? card.unit_price)}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>

      {result.unresolved.length > 0 && (
        <div
          className="rounded-lg border border-slate-600 p-3 text-xs text-slate-300"
          data-testid="suggestion-unresolved"
        >
          <p className="font-medium mb-1">
            {t("deckSuggest.result.unresolved", {
              defaultValue: "Cartas não encontradas no catálogo",
            })}
          </p>
          <ul className="list-disc list-inside">
            {result.unresolved.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      {suggestion.saved_deck_id != null ? (
        <Link
          to={`/decks/${suggestion.saved_deck_id}`}
          className="inline-block px-6 py-2 rounded-md text-sm font-medium bg-cyan-600 text-white hover:bg-cyan-500"
          data-testid="suggestion-view-deck"
        >
          {t("deckSuggest.result.viewDeck", { defaultValue: "Ver deck salvo" })}
        </Link>
      ) : (
        <div className="space-y-2">
          <label className="text-sm text-slate-400 block">
            {t("deckBuild.deckName", { defaultValue: "Nome do deck" })}
            <input
              type="text"
              value={deckName}
              onChange={(e) => setDeckName(e.target.value)}
              maxLength={300}
              className="mt-1 w-full px-3 py-2 bg-slate-700 text-white rounded-md border border-slate-600 focus:border-cyan-500 focus:outline-none"
              data-testid="suggestion-deck-name-input"
            />
          </label>
          {saveError && (
            <p className="text-sm text-red-400" data-testid="suggestion-save-error">
              {saveError}
            </p>
          )}
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 rounded-md text-sm font-medium bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-40"
            data-testid="suggestion-save-btn"
          >
            {saving
              ? t("deckSuggest.result.saving", { defaultValue: "Salvando..." })
              : t("deckSuggest.result.save", { defaultValue: "Salvar como deck" })}
          </button>
        </div>
      )}
    </div>
  );
}
