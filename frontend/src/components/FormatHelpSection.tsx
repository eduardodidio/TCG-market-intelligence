import { useState } from "react";
import { useTranslation } from "react-i18next";

export function FormatHelpSection() {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  return (
    <div data-testid="format-help-section">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-cyan-400 transition-colors"
        data-testid="format-help-toggle"
      >
        <svg
          className={`h-4 w-4 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {t("batchAdd.formatHelpToggle")}
      </button>

      {expanded && (
        <div
          className="mt-2 p-3 rounded-md bg-slate-700/50 border border-slate-600 text-sm text-slate-300 space-y-2"
          data-testid="format-help-content"
        >
          <p className="font-medium text-slate-200">{t("batchAdd.formatHelpTitle")}</p>
          <pre className="font-mono text-xs text-slate-400 whitespace-pre-wrap">
{`1 Lightning Bolt
4 Counterspell [MH2]
2 Sol Ring [CMR] NM EN
1 Black Lotus [LEA] SP EN foil
3 Swords to Plowshares`}
          </pre>
          <ul className="list-disc list-inside text-xs text-slate-400 space-y-1">
            <li>{t("batchAdd.formatRule1")}</li>
            <li>{t("batchAdd.formatRule2")}</li>
            <li>{t("batchAdd.formatRule3")}</li>
            <li>{t("batchAdd.formatRule4")}</li>
          </ul>
        </div>
      )}
    </div>
  );
}
