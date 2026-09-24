import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { searchCommanders } from "../../api/decks";
import type { CommanderSearchResult } from "../../types/api";

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;

type SearchStatus = "idle" | "loading" | "done" | "error";

export interface CommanderSearchProps {
  selected: CommanderSearchResult | null;
  onSelect: (c: CommanderSearchResult) => void;
  onClear: () => void;
}

export function getCommanderImageUrl(c: CommanderSearchResult): string | null {
  if (c.image_uri) return c.image_uri;
  if (c.set_code && c.collector_number) {
    return `https://api.scryfall.com/cards/${c.set_code}/${c.collector_number}?format=image&version=small`;
  }
  return null;
}

export function CommanderSearch({
  selected,
  onSelect,
  onClear,
}: CommanderSearchProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CommanderSearchResult[]>([]);
  const [status, setStatus] = useState<SearchStatus>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const reqSeq = useRef(0);

  const trimmed = query.trim();

  // Debounced search; stale responses are dropped via the request sequence.
  useEffect(() => {
    if (trimmed.length < MIN_QUERY_LENGTH) {
      reqSeq.current += 1; // invalidate any in-flight request
      setResults([]);
      setStatus("idle");
      setErrorMsg(null);
      return;
    }

    const timer = setTimeout(async () => {
      const seq = ++reqSeq.current;
      setStatus("loading");
      setErrorMsg(null);
      let nextStatus: SearchStatus = "done";
      try {
        const resp = await searchCommanders(trimmed);
        if (seq !== reqSeq.current) return;
        if (resp.errors && resp.errors.length > 0) {
          nextStatus = "error";
          setErrorMsg(resp.errors[0].message);
          setResults([]);
        } else {
          setResults(resp.data ?? []);
        }
      } catch (err) {
        if (seq !== reqSeq.current) return;
        nextStatus = "error";
        setErrorMsg(err instanceof Error ? err.message : String(err));
        setResults([]);
      } finally {
        if (seq === reqSeq.current) setStatus(nextStatus);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [trimmed]);

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={t("deckBuild.searchCommander", {
          defaultValue: "Search for a legendary creature...",
        })}
        className="w-full px-4 py-2 bg-slate-700 text-white rounded-md border border-slate-600 focus:border-cyan-500 focus:outline-none mb-4"
        data-testid="commander-search"
      />
      {status === "loading" && (
        <p
          className="text-xs text-slate-400 mb-2"
          data-testid="commander-search-loading"
        >
          {t("common.searching", { defaultValue: "Searching..." })}
        </p>
      )}
      {status === "error" && (
        <div
          className="mb-4 p-3 rounded-md bg-red-900/20 border border-red-700/50 text-red-400 text-sm"
          data-testid="commander-search-error"
        >
          {t("deckBuild.commanderSearchError", {
            defaultValue: "Commander search failed",
          })}
          {errorMsg ? `: ${errorMsg}` : ""}
        </div>
      )}
      {status === "done" &&
        results.length === 0 &&
        trimmed.length >= MIN_QUERY_LENGTH && (
          <p
            className="text-sm text-slate-400 mb-4"
            data-testid="commander-search-empty"
          >
            {t("deckBuild.noCommandersFound", {
              defaultValue: "No commanders found for",
            })}{" "}
            “{trimmed}”
          </p>
        )}
      {selected && (
        <div
          className="mb-4 p-3 rounded-lg bg-cyan-900/20 border border-cyan-700/50 flex items-center gap-3"
          data-testid="selected-commander"
        >
          <p className="text-sm text-white font-medium">{selected.name_en}</p>
          <span className="text-xs text-slate-400">
            {selected.color_identity || "C"}
          </span>
          <button
            onClick={onClear}
            className="ml-auto text-xs text-red-400 hover:text-red-300"
            data-testid="selected-commander-clear"
          >
            {t("common.remove", { defaultValue: "Remove" })}
          </button>
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2 max-h-96 overflow-y-auto">
        {results.map((c) => {
          const imgUrl = getCommanderImageUrl(c);
          const showPt = !!c.name_pt && c.name_pt !== c.name_en;
          return (
            <button
              key={c.card_id}
              onClick={() => onSelect(c)}
              className={`p-2 rounded-lg border text-left transition-all ${
                selected?.card_id === c.card_id
                  ? "border-cyan-500 ring-1 ring-cyan-500/50"
                  : "border-slate-600 hover:border-slate-500"
              }`}
              data-testid={`commander-option-${c.card_id}`}
            >
              {imgUrl && (
                <img
                  src={imgUrl}
                  alt={c.name_en}
                  className="w-full rounded aspect-[488/680] object-cover mb-1"
                  loading="lazy"
                />
              )}
              <p className="text-xs text-white truncate">{c.name_en}</p>
              {showPt && (
                <p className="text-xs text-slate-400 truncate">{c.name_pt}</p>
              )}
              <p className="text-xs text-slate-500">
                {c.color_identity || "C"}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
