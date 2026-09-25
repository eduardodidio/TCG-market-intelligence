import { useTranslation } from "react-i18next";

export type DeckBuildMode = "manual" | "suggestion";

interface DeckBuildModeChooserProps {
  onChoose: (mode: DeckBuildMode) => void;
}

export function DeckBuildModeChooser({ onChoose }: DeckBuildModeChooserProps) {
  const { t } = useTranslation();

  const options: { mode: DeckBuildMode; title: string; desc: string }[] = [
    {
      mode: "manual",
      title: t("deckSuggest.mode.manualTitle", {
        defaultValue: "Build my own deck",
      }),
      desc: t("deckSuggest.mode.manualDesc", {
        defaultValue:
          "Pick format, colors and archetype — generated instantly.",
      }),
    },
    {
      mode: "suggestion",
      title: t("deckSuggest.mode.suggestionTitle", {
        defaultValue: "Deck suggestion",
      }),
      desc: t("deckSuggest.mode.suggestionDesc", {
        defaultValue:
          "Claude builds a deck around your collection. Processed once a day.",
      }),
    },
  ];

  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 gap-4"
      data-testid="mode-chooser"
    >
      {options.map(({ mode, title, desc }) => (
        <button
          key={mode}
          type="button"
          onClick={() => onChoose(mode)}
          aria-describedby={`mode-option-${mode}-desc`}
          className="p-6 rounded-lg border text-left transition-all bg-slate-800 border-slate-600 hover:border-slate-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
          data-testid={`mode-option-${mode}`}
        >
          <p className="text-base font-semibold text-white">{title}</p>
          <p
            id={`mode-option-${mode}-desc`}
            className="text-sm text-slate-400 mt-2"
          >
            {desc}
          </p>
        </button>
      ))}
    </div>
  );
}
