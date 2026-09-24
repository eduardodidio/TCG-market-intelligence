import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createDeckSuggestion,
  MTG_COLOR_KEYS,
  SUGGESTION_ARCHETYPES,
  SUGGESTION_FORMATS,
} from "../../api/deckSuggestions";
import type { CommanderSearchResult } from "../../types/api";
import type {
  DeckSuggestion,
  DeckSuggestionCreate,
} from "../../types/deckSuggestions";
import { CommanderSearch } from "./CommanderSearch";

export const NOTES_MAX_LENGTH = 1000;
const COLORLESS = "C";

const COLOR_STYLES: Record<string, { label: string; bg: string; ring: string }> =
  {
    W: { label: "White", bg: "bg-amber-100", ring: "ring-amber-300" },
    U: { label: "Blue", bg: "bg-blue-500", ring: "ring-blue-400" },
    B: { label: "Black", bg: "bg-gray-700", ring: "ring-gray-500" },
    R: { label: "Red", bg: "bg-red-600", ring: "ring-red-400" },
    G: { label: "Green", bg: "bg-green-600", ring: "ring-green-400" },
    C: { label: "Colorless", bg: "bg-slate-400", ring: "ring-slate-300" },
  };

const COLOR_TOGGLES: string[] = [...MTG_COLOR_KEYS, COLORLESS];

export interface SuggestionRequestFormProps {
  onCreated: (s: DeckSuggestion) => void;
}

/**
 * Toggle a color: "C" (colorless) is mutually exclusive with WUBRG.
 * Returned colors are always in WUBRG order.
 */
export function toggleSuggestionColor(colors: string[], key: string): string[] {
  if (key === COLORLESS) {
    return colors.includes(COLORLESS) ? [] : [COLORLESS];
  }
  const base = colors.filter((c) => c !== COLORLESS);
  const next = base.includes(key)
    ? base.filter((c) => c !== key)
    : [...base, key];
  return MTG_COLOR_KEYS.filter((c) => next.includes(c));
}

export function SuggestionRequestForm({ onCreated }: SuggestionRequestFormProps) {
  const { t } = useTranslation();
  const [format, setFormat] = useState<string>(SUGGESTION_FORMATS[0].value);
  const [commander, setCommander] = useState<CommanderSearchResult | null>(
    null,
  );
  const [colors, setColors] = useState<string[]>([]);
  const [archetype, setArchetype] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  // Remounts CommanderSearch so its query/results clear on reset.
  const [searchKey, setSearchKey] = useState(0);

  const isCommander = format === "commander";
  const isValid = isCommander
    ? commander !== null
    : colors.length > 0 && archetype !== null;
  const canSubmit = isValid && !submitting;

  const resetFields = () => {
    setCommander(null);
    setColors([]);
    setArchetype(null);
    setNotes("");
    setSearchKey((k) => k + 1);
  };

  const changeFormat = (value: string) => {
    if (value === format) return;
    setFormat(value);
    resetFields();
    setError(null);
    setSuccess(false);
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;

    const trimmedNotes = notes.trim();
    const body: DeckSuggestionCreate = isCommander
      ? {
          format_name: format,
          commander_card_id: commander!.card_id,
          notes: trimmedNotes || null,
        }
      : {
          format_name: format,
          colors,
          archetype,
          notes: trimmedNotes || null,
        };

    setSubmitting(true);
    setError(null);
    setSuccess(false);
    try {
      const resp = await createDeckSuggestion(body);
      if (resp.errors && resp.errors.length > 0) {
        setError(resp.errors[0].message);
      } else if (resp.data) {
        setSuccess(true);
        resetFields();
        onCreated(resp.data);
      } else {
        setError(
          t("deckSuggest.form.genericError", {
            defaultValue: "Could not register the request. Try again.",
          }),
        );
      }
    } catch {
      setError(
        t("deckSuggest.form.genericError", {
          defaultValue: "Could not register the request. Try again.",
        }),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    // Not a <form>: CommanderSearch renders untyped buttons that would submit it.
    <div
      className="bg-slate-800 rounded-lg border border-slate-700 p-4 space-y-4"
      data-testid="suggestion-form"
    >
      <div>
        <p className="text-sm text-slate-300 mb-2">
          {t("deckSuggest.form.format", { defaultValue: "Format" })}
        </p>
        <div className="flex flex-wrap gap-2">
          {SUGGESTION_FORMATS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => changeFormat(f.value)}
              aria-pressed={format === f.value}
              className={`px-3 py-1.5 rounded-md border text-sm transition-colors ${
                format === f.value
                  ? "border-cyan-500 bg-cyan-900/30 text-white"
                  : "border-slate-600 text-slate-300 hover:border-slate-500"
              }`}
              data-testid={`suggestion-format-${f.value}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {isCommander ? (
        <div>
          <p className="text-sm text-slate-300 mb-2">
            {t("deckSuggest.form.commander", { defaultValue: "Commander" })}
          </p>
          <CommanderSearch
            key={searchKey}
            selected={commander}
            onSelect={setCommander}
            onClear={() => setCommander(null)}
          />
        </div>
      ) : (
        <>
          <div>
            <p className="text-sm text-slate-300 mb-2">
              {t("deckSuggest.form.colors", { defaultValue: "Colors" })}
            </p>
            <div className="flex flex-wrap gap-3">
              {COLOR_TOGGLES.map((key) => {
                const style = COLOR_STYLES[key];
                const active = colors.includes(key);
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() =>
                      setColors((prev) => toggleSuggestionColor(prev, key))
                    }
                    aria-pressed={active}
                    className={`w-12 h-12 rounded-full flex items-center justify-center text-base font-bold transition-all ${
                      style.bg
                    } ${
                      active
                        ? `ring-2 ${style.ring} scale-110`
                        : "opacity-40 hover:opacity-70"
                    }`}
                    data-testid={`suggestion-color-${key}`}
                    title={style.label}
                  >
                    <span className="text-slate-900 drop-shadow">{key}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <p className="text-sm text-slate-300 mb-2">
              {t("deckSuggest.form.archetype", { defaultValue: "Archetype" })}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {SUGGESTION_ARCHETYPES.map((a) => (
                <button
                  key={a.value}
                  type="button"
                  onClick={() => setArchetype(a.value)}
                  aria-pressed={archetype === a.value}
                  className={`p-3 rounded-lg border text-sm text-left transition-colors ${
                    archetype === a.value
                      ? "border-cyan-500 bg-cyan-900/30 text-white"
                      : "border-slate-600 text-slate-300 hover:border-slate-500"
                  }`}
                  data-testid={`suggestion-archetype-${a.value}`}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      <div>
        <label
          htmlFor="suggestion-notes"
          className="block text-sm text-slate-300 mb-2"
        >
          {t("deckSuggest.form.notes", {
            defaultValue: "Notes (optional)",
          })}
        </label>
        <textarea
          id="suggestion-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={NOTES_MAX_LENGTH}
          rows={3}
          placeholder={t("deckSuggest.form.notesPlaceholder", {
            defaultValue: "e.g. focus on +1/+1 counters, budget-friendly...",
          })}
          className="w-full px-3 py-2 bg-slate-700 text-white rounded-md border border-slate-600 focus:border-cyan-500 focus:outline-none text-sm"
          data-testid="suggestion-notes"
        />
        <p
          className="text-xs text-slate-500 text-right"
          data-testid="suggestion-notes-counter"
        >
          {notes.length}/{NOTES_MAX_LENGTH}
        </p>
      </div>

      {error && (
        <div
          className="p-3 rounded-md bg-red-900/20 border border-red-700/50 text-red-400 text-sm"
          data-testid="suggestion-error"
        >
          {error}
        </div>
      )}
      {success && (
        <div
          className="p-3 rounded-md bg-green-900/20 border border-green-700/50 text-green-400 text-sm"
          data-testid="suggestion-success"
        >
          {t("deckSuggest.form.success", {
            defaultValue:
              "Request registered! Your suggestion will be generated in the next daily run.",
          })}
        </div>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full sm:w-auto px-6 py-2 rounded-md bg-cyan-600 text-white font-medium hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed"
        data-testid="suggestion-submit"
      >
        {submitting
          ? t("deckSuggest.form.submitting", { defaultValue: "Sending..." })
          : t("deckSuggest.form.submit", { defaultValue: "Request suggestion" })}
      </button>
    </div>
  );
}
