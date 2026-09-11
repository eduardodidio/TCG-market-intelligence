import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { scryfallSetIconUrl } from "../utils/scryfall";

interface SetCompletionBarProps {
  setCode: string;
  setName: string;
  owned: number;
  total: number;
  hasCatalog?: boolean;
}

interface SetCompletionSectionProps {
  entries: { set_code: string; set_name: string; owned: number; total: number; has_catalog?: boolean }[];
}

const LS_KEY = "tcg_set_completion_open";

/**
 * Collapsible wrapper that shows a summary line and toggles the set list.
 * Persists expand/collapse preference in localStorage.
 */
export function SetCompletionSection({ entries }: SetCompletionSectionProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(() => localStorage.getItem(LS_KEY) === "1");

  const toggle = () => {
    setOpen((prev) => {
      const next = !prev;
      localStorage.setItem(LS_KEY, next ? "1" : "0");
      return next;
    });
  };

  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={toggle}
        className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white transition-colors mb-2"
        data-testid="toggle-set-completion"
      >
        <svg
          className={`h-4 w-4 transition-transform ${open ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {t("collection.setCompletion", { defaultValue: "Set Completion" })}
        <span className="text-slate-500 text-xs" data-testid="set-completion-count">
          ({entries.length})
        </span>
      </button>
      {open && (
        <div
          className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50 max-h-60 overflow-y-auto"
          data-testid="set-completion-section"
        >
          {entries.map((entry) => (
            <SetCompletionBar
              key={entry.set_code}
              setCode={entry.set_code}
              setName={entry.set_name}
              owned={entry.owned}
              total={entry.total}
              hasCatalog={entry.has_catalog}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Progress bar showing X/Y cards owned per set.
 * Gradient from slate to cyan; gold highlight at 100%.
 * Displays a Scryfall set icon, and clicking navigates to the filtered collection.
 *
 * When hasCatalog is false, shows "X cards (no catalog)" instead of "X of Y"
 * and does not apply gold 100% styling.
 */
export function SetCompletionBar({ setCode, setName, owned, total, hasCatalog }: SetCompletionBarProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [imgError, setImgError] = useState(false);

  const noCatalog = hasCatalog === false;
  const pct = !noCatalog && total > 0 ? Math.min((owned / total) * 100, 100) : 0;
  const isComplete = !noCatalog && pct >= 100;

  const handleClick = () => {
    if (noCatalog) {
      navigate(`/collection?set=${setCode}`);
    } else {
      navigate(`/catalog?set_code=${setCode}&owned_view=1`);
    }
  };

  return (
    <div
      className="flex items-center gap-3 py-1.5 cursor-pointer rounded hover:bg-slate-700/40 transition-colors px-1 -mx-1"
      data-testid={`set-completion-${setCode}`}
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      {/* Set icon + code badge */}
      <span className="inline-flex items-center gap-1.5 w-16 px-1.5 py-0.5 text-xs font-mono bg-slate-700 text-slate-400 rounded shrink-0">
        {imgError ? null : (
          <img
            src={scryfallSetIconUrl(setCode)}
            alt={setCode}
            className="w-4 h-4 invert brightness-200"
            onError={() => setImgError(true)}
            data-testid={`set-icon-${setCode}`}
          />
        )}
        <span className="truncate">{setCode}</span>
      </span>

      {/* Set name */}
      <span className="text-sm text-slate-300 truncate w-32 shrink-0" title={setName}>
        {setName}
      </span>

      {/* Progress bar */}
      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
        {!noCatalog && (
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isComplete
                ? "bg-gradient-to-r from-amber-400 to-amber-500"
                : "bg-gradient-to-r from-slate-500 to-cyan-400"
            }`}
            style={{ width: `${pct}%` }}
            data-testid="completion-bar-fill"
          />
        )}
      </div>

      {/* Label */}
      <span
        className={`text-xs font-medium shrink-0 w-24 text-right ${
          isComplete ? "text-amber-400" : "text-slate-400"
        }`}
        data-testid="completion-label"
      >
        {noCatalog
          ? t("collection.setNoCatalog", {
              owned,
              defaultValue: "{{owned}} cards (no catalog)",
            })
          : isComplete
            ? t("collection.setComplete", { defaultValue: "Complete!" })
            : t("collection.setCompletionOf", {
                owned,
                total,
                defaultValue: "{{owned}} of {{total}}",
              })}
      </span>
    </div>
  );
}
