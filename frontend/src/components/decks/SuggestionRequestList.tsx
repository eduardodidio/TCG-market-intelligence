import { useTranslation } from "react-i18next";
import { EmptyState } from "../EmptyState";
import { formatDate } from "../../utils/format";
import type { DeckSuggestion, SuggestionStatus } from "../../types/deckSuggestions";

export interface SuggestionRequestListProps {
  items: DeckSuggestion[];
  selectedId: number | null;
  loading: boolean;
  onSelect: (id: number) => void;
  onRefresh: () => void;
  onDelete: (id: number) => void;
}

const FORMAT_LABELS: Record<string, string> = {
  commander: "Commander",
  standard: "Standard",
  pioneer: "Pioneer",
  modern: "Modern",
  legacy: "Legacy",
  vintage: "Vintage",
  pauper: "Pauper",
  casual: "Casual",
};

const STATUS_STYLES: Record<SuggestionStatus, { className: string; label: string }> = {
  pending: {
    className: "bg-amber-500/15 text-amber-300 border-amber-500/40",
    label: "Na fila",
  },
  processing: {
    className: "bg-cyan-500/15 text-cyan-300 border-cyan-500/40",
    label: "Processando",
  },
  done: {
    className: "bg-green-500/15 text-green-300 border-green-500/40",
    label: "Pronto",
  },
  failed: {
    className: "bg-red-500/15 text-red-300 border-red-500/40",
    label: "Falhou",
  },
};

export function formatLabel(formatName: string): string {
  return (
    FORMAT_LABELS[formatName] ??
    formatName.charAt(0).toUpperCase() + formatName.slice(1)
  );
}

/** Row label: commander name, or colors + archetype for other formats. */
export function suggestionLabel(s: DeckSuggestion): string {
  if (s.commander_name) return s.commander_name;
  const colors = s.colors.join("");
  return [colors, s.archetype].filter(Boolean).join(" · ");
}

export function SuggestionRequestList({
  items,
  selectedId,
  loading,
  onSelect,
  onRefresh,
  onDelete,
}: SuggestionRequestListProps) {
  const { t } = useTranslation();

  const handleDelete = (id: number) => {
    const ok = window.confirm(
      t("deckSuggestions.list.confirmDelete", {
        defaultValue: "Excluir este pedido de sugestão?",
      }),
    );
    if (ok) onDelete(id);
  };

  return (
    <div data-testid="suggestion-list" className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-200">
          {t("deckSuggestions.list.title", { defaultValue: "Meus pedidos" })}
        </h3>
        <div className="flex items-center gap-2">
          {loading && (
            <div
              data-testid="suggestion-list-loading"
              role="status"
              aria-label={t("deckSuggestions.list.loading", {
                defaultValue: "Carregando...",
              })}
              className="h-4 w-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"
            />
          )}
          <button
            type="button"
            data-testid="suggestion-refresh"
            onClick={onRefresh}
            disabled={loading}
            className="rounded-md border border-slate-600 px-3 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {t("deckSuggestions.list.refresh", { defaultValue: "Atualizar" })}
          </button>
        </div>
      </div>

      {items.length === 0 && !loading ? (
        <div data-testid="suggestion-list-empty">
          <EmptyState
            compact
            title={t("deckSuggestions.list.emptyTitle", {
              defaultValue: "Nenhum pedido ainda",
            })}
            description={t("deckSuggestions.list.emptyDescription", {
              defaultValue: "Crie um pedido de sugestão para vê-lo aqui.",
            })}
          />
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((s) => {
            const selected = s.id === selectedId;
            const status = STATUS_STYLES[s.status];
            return (
              <li
                key={s.id}
                data-testid={`suggestion-row-${s.id}`}
                aria-selected={selected}
                className={`flex items-center gap-2 rounded-lg border px-3 py-2 transition-colors ${
                  selected
                    ? "border-cyan-400 bg-cyan-500/10"
                    : "border-slate-700 bg-slate-800/60 hover:border-slate-500"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelect(s.id)}
                  className="flex-1 min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs font-semibold uppercase text-slate-400">
                      {formatLabel(s.format_name)}
                    </span>
                    <span className="truncate text-sm text-slate-100">
                      {suggestionLabel(s)}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
                    <span>{formatDate(s.created_at)}</span>
                    {s.status === "done" && s.summary && (
                      <span data-testid={`suggestion-owned-${s.id}`}>
                        {t("deckSuggestions.list.ownedOfTotal", {
                          owned: s.summary.owned_cards,
                          total: s.summary.total_cards,
                          defaultValue: `${s.summary.owned_cards}/${s.summary.total_cards} na coleção`,
                        })}
                      </span>
                    )}
                  </div>
                </button>
                <span
                  data-testid={`suggestion-status-${s.id}`}
                  title={s.status === "failed" ? (s.error_message ?? undefined) : undefined}
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium ${status.className}`}
                >
                  {t(`deckSuggestions.status.${s.status}`, {
                    defaultValue: status.label,
                  })}
                </span>
                {s.status === "pending" && (
                  <button
                    type="button"
                    data-testid={`suggestion-delete-${s.id}`}
                    onClick={() => handleDelete(s.id)}
                    aria-label={t("deckSuggestions.list.delete", {
                      defaultValue: "Excluir pedido",
                    })}
                    className="shrink-0 rounded p-1 text-slate-400 hover:text-red-400 hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                  >
                    ✕
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
