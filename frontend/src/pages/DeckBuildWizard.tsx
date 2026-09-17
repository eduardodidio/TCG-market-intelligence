import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { generateDeck, searchCommanders } from "../api/decks";
import { Breadcrumb } from "../components/Breadcrumb";
import type {
  CommanderSearchResult,
  DeckGenerateParams,
  DeckGenerateResult,
} from "../types/api";

type WizardStep = 1 | 2 | 3 | 4;

const FORMAT_INFO: Record<
  string,
  { label: string; cards: number; desc: string }
> = {
  commander: {
    label: "Commander",
    cards: 100,
    desc: "100-card singleton with a legendary creature as commander.",
  },
  standard: {
    label: "Standard",
    cards: 60,
    desc: "60-card deck with up to 4 copies. Recent sets only.",
  },
  modern: {
    label: "Modern",
    cards: 60,
    desc: "60-card deck with up to 4 copies. 8th Edition forward.",
  },
  legacy: {
    label: "Legacy",
    cards: 60,
    desc: "60-card deck. All sets legal, powerful banned list.",
  },
  pauper: {
    label: "Pauper",
    cards: 60,
    desc: "60-card deck. Commons only.",
  },
  casual: {
    label: "Casual",
    cards: 60,
    desc: "60-card deck. No ban list restrictions.",
  },
};

const ARCHETYPES: Record<string, { label: string; desc: string }> = {
  aggro: {
    label: "Aggro",
    desc: "Fast, creature-heavy. Win before the opponent stabilizes.",
  },
  control: {
    label: "Control",
    desc: "Removal, counters, card draw. Win in the late game.",
  },
  midrange: {
    label: "Midrange",
    desc: "Balanced mix of threats and answers.",
  },
  combo: {
    label: "Combo",
    desc: "Assemble card combinations for powerful synergies.",
  },
  tempo: {
    label: "Tempo",
    desc: "Efficient threats + disruption. Stay one step ahead.",
  },
};

const MTG_COLORS: { key: string; label: string; bg: string; ring: string }[] =
  [
    { key: "W", label: "White", bg: "bg-amber-100", ring: "ring-amber-300" },
    { key: "U", label: "Blue", bg: "bg-blue-500", ring: "ring-blue-400" },
    { key: "B", label: "Black", bg: "bg-gray-700", ring: "ring-gray-500" },
    { key: "R", label: "Red", bg: "bg-red-600", ring: "ring-red-400" },
    { key: "G", label: "Green", bg: "bg-green-600", ring: "ring-green-400" },
  ];

export function DeckBuildWizard() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Wizard state
  const [step, setStep] = useState<WizardStep>(1);
  const [formatName, setFormatName] = useState("");
  const [selectedColors, setSelectedColors] = useState<string[]>([]);
  const [archetype, setArchetype] = useState<string | null>(null);
  const [budgetLimit, setBudgetLimit] = useState<string>("");
  const [prioritizeOwned, setPrioritizeOwned] = useState(false);
  const [deckName, setDeckName] = useState("");

  // Commander search
  const [commanderQuery, setCommanderQuery] = useState("");
  const [commanderResults, setCommanderResults] = useState<
    CommanderSearchResult[]
  >([]);
  const [selectedCommander, setSelectedCommander] =
    useState<CommanderSearchResult | null>(null);
  const [searchingCommanders, setSearchingCommanders] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Generation state
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<DeckGenerateResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isCommanderFormat = formatName === "commander";

  // Debounced commander search
  useEffect(() => {
    if (!isCommanderFormat || commanderQuery.length < 2) {
      setCommanderResults([]);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSearchingCommanders(true);
      const resp = await searchCommanders(commanderQuery);
      if (resp.data) setCommanderResults(resp.data);
      setSearchingCommanders(false);
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [commanderQuery, isCommanderFormat]);

  // Auto-set colors from commander
  useEffect(() => {
    if (selectedCommander?.color_identity) {
      const ci = selectedCommander.color_identity;
      setSelectedColors(
        ci.split("").filter((c) => "WUBRG".includes(c)),
      );
    }
  }, [selectedCommander]);

  const toggleColor = useCallback((color: string) => {
    setSelectedColors((prev) =>
      prev.includes(color)
        ? prev.filter((c) => c !== color)
        : [...prev, color],
    );
  }, []);

  const canProceedStep1 = formatName !== "";
  const canProceedStep2 = isCommanderFormat
    ? selectedCommander !== null
    : selectedColors.length > 0;
  const canProceedStep3 = true; // archetype is optional

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setError(null);

    const params: DeckGenerateParams = {
      format_name: formatName,
      commander_card_id: selectedCommander?.card_id ?? null,
      colors: selectedColors,
      archetype: archetype,
      budget_limit: budgetLimit ? parseFloat(budgetLimit) : null,
      prioritize_owned: prioritizeOwned,
      deck_name: deckName || undefined,
    };

    const resp = await generateDeck(params);
    if (resp.errors.length > 0) {
      setError(resp.errors[0].message);
    } else if (resp.data) {
      setResult(resp.data);
      setDeckName(resp.data.name);
      setStep(4);
    }
    setGenerating(false);
  }, [
    formatName,
    selectedCommander,
    selectedColors,
    archetype,
    budgetLimit,
    prioritizeOwned,
    deckName,
  ]);

  const handleRegenerate = useCallback(async () => {
    setResult(null);
    await handleGenerate();
  }, [handleGenerate]);

  const handleSave = useCallback(() => {
    if (result) {
      navigate(`/decks/${result.deck_id}`);
    }
  }, [result, navigate]);

  const getCommanderImageUrl = (c: CommanderSearchResult) => {
    if (c.image_uri) return c.image_uri;
    if (c.set_code && c.collector_number) {
      return `https://api.scryfall.com/cards/${c.set_code}/${c.collector_number}?format=image&version=small`;
    }
    return null;
  };

  return (
    <div data-testid="page-deck-build-wizard">
      <Breadcrumb
        items={[
          { label: t("nav.myDecks", { defaultValue: "My Decks" }), to: "/decks" },
          { label: t("deckBuild.title", { defaultValue: "Build Deck" }) },
        ]}
      />

      <h1 className="text-2xl font-bold text-white mb-6">
        {t("deckBuild.title", { defaultValue: "Deck Builder" })}
      </h1>

      {/* Progress indicator */}
      <div className="flex items-center gap-2 mb-8" data-testid="wizard-progress">
        {([1, 2, 3, 4] as WizardStep[]).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                s === step
                  ? "bg-cyan-500 text-white"
                  : s < step
                    ? "bg-green-600 text-white"
                    : "bg-slate-700 text-slate-400"
              }`}
            >
              {s < step ? (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                s
              )}
            </div>
            {s < 4 && (
              <div
                className={`w-12 h-0.5 ${
                  s < step ? "bg-green-600" : "bg-slate-700"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {error && (
        <div
          className="mb-4 p-3 rounded-md bg-red-900/20 border border-red-700/50 text-red-400 text-sm"
          data-testid="wizard-error"
        >
          {error}
        </div>
      )}

      {/* Step 1: Format Selection */}
      {step === 1 && (
        <div data-testid="wizard-step-1">
          <h2 className="text-lg font-semibold text-white mb-4">
            {t("deckBuild.selectFormat", {
              defaultValue: "Select Format",
            })}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(FORMAT_INFO).map(([key, info]) => (
              <button
                key={key}
                onClick={() => setFormatName(key)}
                className={`p-4 rounded-lg border text-left transition-all ${
                  formatName === key
                    ? "bg-cyan-900/30 border-cyan-500 ring-1 ring-cyan-500/50"
                    : "bg-slate-800 border-slate-600 hover:border-slate-500"
                }`}
                data-testid={`format-option-${key}`}
              >
                <p className="text-sm font-semibold text-white">
                  {info.label}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {info.cards} cards
                </p>
                <p className="text-xs text-slate-500 mt-1">{info.desc}</p>
              </button>
            ))}
          </div>
          <div className="flex justify-end mt-6">
            <button
              onClick={() => setStep(2)}
              disabled={!canProceedStep1}
              className="px-6 py-2 rounded-md text-sm font-medium bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              data-testid="step1-next"
            >
              {t("common.next", { defaultValue: "Next" })}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Commander/Colors */}
      {step === 2 && (
        <div data-testid="wizard-step-2">
          <h2 className="text-lg font-semibold text-white mb-4">
            {isCommanderFormat
              ? t("deckBuild.selectCommander", {
                  defaultValue: "Select Commander",
                })
              : t("deckBuild.selectColors", {
                  defaultValue: "Select Colors",
                })}
          </h2>

          {isCommanderFormat ? (
            <div>
              <input
                type="text"
                value={commanderQuery}
                onChange={(e) => setCommanderQuery(e.target.value)}
                placeholder={t("deckBuild.searchCommander", {
                  defaultValue: "Search for a legendary creature...",
                })}
                className="w-full px-4 py-2 bg-slate-700 text-white rounded-md border border-slate-600 focus:border-cyan-500 focus:outline-none mb-4"
                data-testid="commander-search"
              />
              {searchingCommanders && (
                <p className="text-xs text-slate-400 mb-2">
                  {t("common.searching", { defaultValue: "Searching..." })}
                </p>
              )}
              {selectedCommander && (
                <div
                  className="mb-4 p-3 rounded-lg bg-cyan-900/20 border border-cyan-700/50 flex items-center gap-3"
                  data-testid="selected-commander"
                >
                  <p className="text-sm text-white font-medium">
                    {selectedCommander.name_en}
                  </p>
                  <span className="text-xs text-slate-400">
                    {selectedCommander.color_identity || "C"}
                  </span>
                  <button
                    onClick={() => {
                      setSelectedCommander(null);
                      setSelectedColors([]);
                    }}
                    className="ml-auto text-xs text-red-400 hover:text-red-300"
                  >
                    {t("common.remove", { defaultValue: "Remove" })}
                  </button>
                </div>
              )}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2 max-h-96 overflow-y-auto">
                {commanderResults.map((c) => {
                  const imgUrl = getCommanderImageUrl(c);
                  return (
                    <button
                      key={c.card_id}
                      onClick={() => setSelectedCommander(c)}
                      className={`p-2 rounded-lg border text-left transition-all ${
                        selectedCommander?.card_id === c.card_id
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
                      <p className="text-xs text-white truncate">
                        {c.name_en}
                      </p>
                      <p className="text-xs text-slate-500">
                        {c.color_identity || "C"}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div>
              <p className="text-sm text-slate-400 mb-4">
                {t("deckBuild.pickColors", {
                  defaultValue: "Pick one or more colors for your deck.",
                })}
              </p>
              <div className="flex gap-3" data-testid="color-picker">
                {MTG_COLORS.map((c) => (
                  <button
                    key={c.key}
                    onClick={() => toggleColor(c.key)}
                    className={`w-14 h-14 rounded-full flex items-center justify-center text-lg font-bold transition-all ${
                      c.bg
                    } ${
                      selectedColors.includes(c.key)
                        ? `ring-2 ${c.ring} scale-110`
                        : "opacity-40 hover:opacity-70"
                    }`}
                    data-testid={`color-toggle-${c.key}`}
                    title={c.label}
                  >
                    {c.key}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-between mt-6">
            <button
              onClick={() => setStep(1)}
              className="px-6 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white transition-colors"
              data-testid="step2-back"
            >
              {t("common.back", { defaultValue: "Back" })}
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!canProceedStep2}
              className="px-6 py-2 rounded-md text-sm font-medium bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              data-testid="step2-next"
            >
              {t("common.next", { defaultValue: "Next" })}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Archetype & Budget */}
      {step === 3 && (
        <div data-testid="wizard-step-3">
          <h2 className="text-lg font-semibold text-white mb-4">
            {t("deckBuild.archetypeBudget", {
              defaultValue: "Archetype & Budget",
            })}
          </h2>

          <div className="mb-6">
            <p className="text-sm text-slate-400 mb-3">
              {t("deckBuild.selectArchetype", {
                defaultValue: "Select an archetype (optional):",
              })}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(ARCHETYPES).map(([key, info]) => (
                <button
                  key={key}
                  onClick={() =>
                    setArchetype(archetype === key ? null : key)
                  }
                  className={`p-3 rounded-lg border text-left transition-all ${
                    archetype === key
                      ? "bg-cyan-900/30 border-cyan-500 ring-1 ring-cyan-500/50"
                      : "bg-slate-800 border-slate-600 hover:border-slate-500"
                  }`}
                  data-testid={`archetype-option-${key}`}
                >
                  <p className="text-sm font-semibold text-white">
                    {info.label}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">{info.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <p className="text-sm text-slate-400 mb-3">
              {t("deckBuild.budgetLabel", {
                defaultValue: "Budget limit (BRL, optional):",
              })}
            </p>
            <div className="flex items-center gap-3">
              <input
                type="number"
                value={budgetLimit}
                onChange={(e) => setBudgetLimit(e.target.value)}
                placeholder="No limit"
                min="0"
                className="w-40 px-3 py-2 bg-slate-700 text-white rounded-md border border-slate-600 focus:border-cyan-500 focus:outline-none"
                data-testid="budget-input"
              />
              <div className="flex gap-2">
                {[100, 500, 1000].map((preset) => (
                  <button
                    key={preset}
                    onClick={() => setBudgetLimit(String(preset))}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      budgetLimit === String(preset)
                        ? "bg-cyan-600 text-white"
                        : "bg-slate-700 text-slate-400 hover:text-white"
                    }`}
                    data-testid={`budget-preset-${preset}`}
                  >
                    R${preset}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mb-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={prioritizeOwned}
                onChange={(e) => setPrioritizeOwned(e.target.checked)}
                className="rounded border-slate-600 bg-slate-700 text-cyan-500 focus:ring-cyan-500"
                data-testid="prioritize-owned"
              />
              <span className="text-sm text-slate-300">
                {t("deckBuild.prioritizeOwned", {
                  defaultValue: "Prioritize cards I already own",
                })}
              </span>
            </label>
          </div>

          <div className="flex justify-between mt-6">
            <button
              onClick={() => setStep(2)}
              className="px-6 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white transition-colors"
              data-testid="step3-back"
            >
              {t("common.back", { defaultValue: "Back" })}
            </button>
            <button
              onClick={handleGenerate}
              disabled={generating || !canProceedStep3}
              className="px-6 py-2 rounded-md text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              data-testid="generate-btn"
            >
              {generating
                ? t("deckBuild.generating", {
                    defaultValue: "Generating...",
                  })
                : t("deckBuild.generate", {
                    defaultValue: "Generate Deck",
                  })}
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Review & Save */}
      {step === 4 && result && (
        <div data-testid="wizard-step-4">
          <h2 className="text-lg font-semibold text-white mb-4">
            {t("deckBuild.reviewDeck", { defaultValue: "Review Deck" })}
          </h2>

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <div className="mb-4 space-y-2" data-testid="generate-warnings">
              {result.warnings.map((w, i) => (
                <div
                  key={i}
                  className="p-2 rounded-md bg-amber-900/20 border border-amber-700/50 text-amber-400 text-xs"
                >
                  {w}
                </div>
              ))}
            </div>
          )}

          {/* Stats summary */}
          <div
            className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6"
            data-testid="generate-stats"
          >
            <div className="p-3 rounded-lg bg-slate-800 border border-slate-600">
              <p className="text-xs text-slate-400">
                {t("deckBuild.totalCards", { defaultValue: "Total Cards" })}
              </p>
              <p className="text-lg font-bold text-white" data-testid="gen-total-cards">
                {result.total_cards}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-slate-800 border border-slate-600">
              <p className="text-xs text-slate-400">
                {t("deckBuild.lands", { defaultValue: "Lands" })}
              </p>
              <p className="text-lg font-bold text-white">
                {result.land_count}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-slate-800 border border-slate-600">
              <p className="text-xs text-slate-400">
                {t("deckBuild.nonlands", { defaultValue: "Non-Lands" })}
              </p>
              <p className="text-lg font-bold text-white">
                {result.nonland_count}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-slate-800 border border-slate-600">
              <p className="text-xs text-slate-400">
                {t("deckBuild.totalValue", { defaultValue: "Total Value" })}
              </p>
              <p className="text-lg font-bold text-white">
                {result.total_value !== null
                  ? `R$ ${result.total_value.toFixed(2)}`
                  : "N/A"}
              </p>
            </div>
          </div>

          {/* Deck name input */}
          <div className="mb-4">
            <label className="text-sm text-slate-400 block mb-1">
              {t("deckBuild.deckName", { defaultValue: "Deck Name" })}
            </label>
            <input
              type="text"
              value={deckName}
              onChange={(e) => setDeckName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 text-white rounded-md border border-slate-600 focus:border-cyan-500 focus:outline-none"
              data-testid="deck-name-input"
            />
          </div>

          {/* Card grid */}
          <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-8 gap-2 mb-6" data-testid="generated-cards-grid">
            {result.cards.map((card, i) => {
              const imgUrl =
                card.image_uri ||
                (card.set_code && card.collector_number
                  ? `https://api.scryfall.com/cards/${card.set_code}/${card.collector_number}?format=image&version=small`
                  : null);
              return (
                <div
                  key={`${card.card_id ?? card.name_en}-${i}`}
                  className={`rounded-lg border ${
                    card.is_owned
                      ? "border-green-600/50"
                      : "border-slate-600/50"
                  } overflow-hidden`}
                  title={`${card.quantity}x ${card.name_en}${card.price ? ` (R$ ${card.price.toFixed(2)})` : ""}`}
                >
                  {imgUrl ? (
                    <img
                      src={imgUrl}
                      alt={card.name_en}
                      className="w-full aspect-[488/680] object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full aspect-[488/680] bg-slate-800 flex items-center justify-center">
                      <p className="text-xs text-slate-500 text-center px-1">
                        {card.name_en}
                      </p>
                    </div>
                  )}
                  {card.quantity > 1 && (
                    <div className="text-center text-xs text-slate-400 py-0.5 bg-slate-800">
                      x{card.quantity}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Action buttons */}
          <div className="flex justify-between">
            <button
              onClick={() => setStep(3)}
              className="px-6 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-white transition-colors"
              data-testid="step4-back"
            >
              {t("common.back", { defaultValue: "Back" })}
            </button>
            <div className="flex gap-3">
              <button
                onClick={handleRegenerate}
                disabled={generating}
                className="px-6 py-2 rounded-md text-sm font-medium bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-40 transition-colors"
                data-testid="regenerate-btn"
              >
                {generating
                  ? t("deckBuild.generating", {
                      defaultValue: "Generating...",
                    })
                  : t("deckBuild.regenerate", {
                      defaultValue: "Regenerate",
                    })}
              </button>
              <button
                onClick={handleSave}
                className="px-6 py-2 rounded-md text-sm font-medium bg-green-600 text-white hover:bg-green-500 transition-colors"
                data-testid="save-deck-btn"
              >
                {t("deckBuild.saveDeck", { defaultValue: "View Deck" })}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
