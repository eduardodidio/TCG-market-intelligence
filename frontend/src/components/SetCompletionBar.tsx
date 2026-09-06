import { useTranslation } from "react-i18next";

interface SetCompletionBarProps {
  setCode: string;
  setName: string;
  owned: number;
  total: number;
}

/**
 * Progress bar showing X/Y cards owned per set.
 * Gradient from slate to cyan; gold highlight at 100%.
 */
export function SetCompletionBar({ setCode, setName, owned, total }: SetCompletionBarProps) {
  const { t } = useTranslation();
  const pct = total > 0 ? Math.min((owned / total) * 100, 100) : 0;
  const isComplete = pct >= 100;

  return (
    <div
      className="flex items-center gap-3 py-1.5"
      data-testid={`set-completion-${setCode}`}
    >
      {/* Set code badge */}
      <span className="inline-block w-12 px-1.5 py-0.5 text-xs font-mono bg-slate-700 text-slate-400 rounded text-center shrink-0">
        {setCode}
      </span>

      {/* Set name */}
      <span className="text-sm text-slate-300 truncate w-32 shrink-0" title={setName}>
        {setName}
      </span>

      {/* Progress bar */}
      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isComplete
              ? "bg-gradient-to-r from-amber-400 to-amber-500"
              : "bg-gradient-to-r from-slate-500 to-cyan-400"
          }`}
          style={{ width: `${pct}%` }}
          data-testid="completion-bar-fill"
        />
      </div>

      {/* Label */}
      <span
        className={`text-xs font-medium shrink-0 w-24 text-right ${
          isComplete ? "text-amber-400" : "text-slate-400"
        }`}
        data-testid="completion-label"
      >
        {isComplete
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
