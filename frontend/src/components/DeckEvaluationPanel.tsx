import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { fetchDeckEvaluation } from "../api/decks";
import type { DeckEvaluation } from "../types/api";

interface Props {
  deckId: number;
}

const TYPE_COLORS: Record<string, string> = {
  Creature: "#22c55e",
  Instant: "#3b82f6",
  Sorcery: "#ef4444",
  Enchantment: "#eab308",
  Artifact: "#9ca3af",
  Land: "#a16207",
  Planeswalker: "#a855f7",
  Other: "#6b7280",
};

const MTG_COLOR_MAP: Record<string, { label: string; hex: string }> = {
  W: { label: "White", hex: "#f5f0e1" },
  U: { label: "Blue", hex: "#0e68ab" },
  B: { label: "Black", hex: "#6b7280" },
  R: { label: "Red", hex: "#dc2626" },
  G: { label: "Green", hex: "#16a34a" },
  C: { label: "Colorless", hex: "#94a3b8" },
};

const FORMAT_OPTIONS = [
  { value: "commander", label: "Commander" },
  { value: "standard", label: "Standard" },
  { value: "modern", label: "Modern" },
  { value: "legacy", label: "Legacy" },
  { value: "pauper", label: "Pauper" },
];

export function DeckEvaluationPanel({ deckId }: Props) {
  const { t } = useTranslation();
  const [evaluation, setEvaluation] = useState<DeckEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [format, setFormat] = useState("commander");

  const loadEvaluation = useCallback(async () => {
    setLoading(true);
    setError(null);
    const resp = await fetchDeckEvaluation(deckId, format);
    if (resp.errors.length > 0) {
      setError(resp.errors[0].message);
    } else {
      setEvaluation(resp.data);
    }
    setLoading(false);
  }, [deckId, format]);

  useEffect(() => {
    loadEvaluation();
  }, [loadEvaluation]);

  if (loading) {
    return (
      <div className="space-y-4" data-testid="evaluation-loading">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-48 bg-slate-800 animate-pulse rounded-lg"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="p-4 rounded-md bg-red-900/20 border border-red-700/50 text-red-400"
        data-testid="evaluation-error"
      >
        {error}
      </div>
    );
  }

  if (!evaluation) return null;

  const manaCurveData = evaluation.mana_curve.map((p) => ({
    cmc: p.cmc === 7 ? "7+" : String(p.cmc),
    count: p.count,
  }));

  const typeData = evaluation.type_distribution.map((t) => ({
    name: t.type_name,
    value: t.count,
  }));

  const colorData = evaluation.color_distribution.map((c) => ({
    name: MTG_COLOR_MAP[c.color]?.label || c.color,
    value: c.pip_count,
    color: MTG_COLOR_MAP[c.color]?.hex || "#6b7280",
  }));

  return (
    <div className="space-y-6" data-testid="deck-evaluation-panel">
      {/* Format selector */}
      <div className="flex items-center gap-2">
        <label className="text-sm text-slate-400">
          {t("deckEval.checkFormat", { defaultValue: "Check format:" })}
        </label>
        <select
          value={format}
          onChange={(e) => setFormat(e.target.value)}
          className="bg-slate-700 text-white text-sm rounded px-3 py-1.5 border border-slate-600 focus:border-cyan-500 focus:outline-none"
          data-testid="format-selector"
        >
          {FORMAT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mana Curve */}
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="mana-curve-section"
        >
          <h3 className="text-sm font-semibold text-white mb-1">
            {t("deckEval.manaCurve", { defaultValue: "Mana Curve" })}
          </h3>
          <p className="text-xs text-slate-400 mb-3">
            {t("deckEval.avgCmc", { defaultValue: "Avg CMC" })}:{" "}
            <span className="text-cyan-400 font-semibold" data-testid="avg-cmc">
              {evaluation.avg_cmc.toFixed(2)}
            </span>
          </p>
          {manaCurveData.length > 0 ? (
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={manaCurveData}>
                  <XAxis
                    dataKey="cmc"
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={30}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #475569",
                      borderRadius: "0.375rem",
                    }}
                    labelStyle={{ color: "#94a3b8" }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 text-center py-8">
              {t("deckEval.noData", { defaultValue: "No data" })}
            </p>
          )}
        </div>

        {/* Type Distribution */}
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="type-dist-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("deckEval.typeDistribution", {
              defaultValue: "Type Distribution",
            })}
          </h3>
          {typeData.length > 0 ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={typeData}
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                    labelLine={false}
                  >
                    {typeData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={TYPE_COLORS[entry.name] || "#6b7280"}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #475569",
                      borderRadius: "0.375rem",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 text-center py-8">
              {t("deckEval.noData", { defaultValue: "No data" })}
            </p>
          )}
        </div>

        {/* Color Distribution */}
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="color-dist-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("deckEval.colorDistribution", {
              defaultValue: "Color Distribution",
            })}
          </h3>
          {colorData.length > 0 ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={colorData}
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                    labelLine={false}
                  >
                    {colorData.map((entry, idx) => (
                      <Cell key={`color-${idx}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #475569",
                      borderRadius: "0.375rem",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 text-center py-8">
              {t("deckEval.noData", { defaultValue: "No data" })}
            </p>
          )}
        </div>

        {/* Land / Nonland Ratio */}
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="land-ratio-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("deckEval.composition", { defaultValue: "Composition" })}
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">
                {t("deckEval.totalCards", { defaultValue: "Total Cards" })}
              </span>
              <span className="text-white font-semibold" data-testid="eval-total-cards">
                {evaluation.total_cards}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">
                {t("deckEval.lands", { defaultValue: "Lands" })}
              </span>
              <span className="text-white" data-testid="eval-land-count">
                {evaluation.land_count}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">
                {t("deckEval.nonlands", { defaultValue: "Non-Lands" })}
              </span>
              <span className="text-white" data-testid="eval-nonland-count">
                {evaluation.nonland_count}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">
                {t("deckEval.colorIdentity", { defaultValue: "Color Identity" })}
              </span>
              <span className="text-white" data-testid="eval-color-identity">
                {evaluation.color_identity.join("") || "C"}
              </span>
            </div>
            {/* Land ratio bar */}
            {evaluation.total_cards > 0 && (
              <div>
                <div className="w-full bg-slate-700 rounded-full h-2.5 mt-2">
                  <div
                    className="bg-amber-600 h-2.5 rounded-full"
                    style={{
                      width: `${(evaluation.land_count / evaluation.total_cards) * 100}%`,
                    }}
                    data-testid="land-ratio-bar"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {((evaluation.land_count / evaluation.total_cards) * 100).toFixed(0)}%{" "}
                  {t("deckEval.lands", { defaultValue: "Lands" })}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Legality */}
      {evaluation.legality && (
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="legality-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("deckEval.legality", { defaultValue: "Format Legality" })}
          </h3>
          <div className="flex items-center gap-2 mb-2">
            {evaluation.legality.is_legal ? (
              <span
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-green-900/30 text-green-400 border border-green-700/50"
                data-testid="legality-badge-legal"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                {t("deckEval.legalIn", {
                  defaultValue: `Legal in ${evaluation.legality.format}`,
                  format: evaluation.legality.format,
                })}
              </span>
            ) : (
              <span
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-red-900/30 text-red-400 border border-red-700/50"
                data-testid="legality-badge-illegal"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
                {t("deckEval.notLegalIn", {
                  defaultValue: `Not legal in ${evaluation.legality.format}`,
                  format: evaluation.legality.format,
                })}
              </span>
            )}
            {!evaluation.legality.card_count_valid && (
              <span className="text-xs text-amber-400">
                {t("deckEval.cardCountInvalid", {
                  defaultValue: "Deck does not meet minimum card count",
                })}
              </span>
            )}
          </div>

          {evaluation.legality.illegal_cards.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-slate-400 mb-1">
                {t("deckEval.illegalCards", { defaultValue: "Illegal cards:" })}
              </p>
              <ul className="text-xs text-red-400 space-y-0.5" data-testid="illegal-cards-list">
                {evaluation.legality.illegal_cards.map((c, i) => (
                  <li key={i}>
                    {c.name_en} ({c.status})
                  </li>
                ))}
              </ul>
            </div>
          )}

          {evaluation.legality.singleton_violations.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-slate-400 mb-1">
                {t("deckEval.singletonViolations", {
                  defaultValue: "Singleton violations:",
                })}
              </p>
              <ul className="text-xs text-amber-400 space-y-0.5">
                {evaluation.legality.singleton_violations.map((name, i) => (
                  <li key={i}>{name}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Budget */}
      {evaluation.budget && (
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="budget-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("deckEval.budget", { defaultValue: "Budget Analysis" })}
          </h3>
          <div className="flex items-center gap-6 mb-3">
            <div>
              <p className="text-xs text-slate-400">
                {t("deckEval.totalValue", { defaultValue: "Total Value" })}
              </p>
              <p className="text-lg font-bold text-white" data-testid="budget-total-value">
                R$ {evaluation.budget.total_value.toFixed(2)}
              </p>
            </div>
            <div className="flex gap-3">
              {Object.entries(evaluation.budget.price_tiers).map(([tier, count]) => (
                <div key={tier} className="text-center">
                  <p className="text-xs text-slate-500 capitalize">{tier}</p>
                  <p className="text-sm text-slate-300 font-medium">{count}</p>
                </div>
              ))}
            </div>
          </div>

          {evaluation.budget.most_expensive.length > 0 && (
            <div>
              <p className="text-xs text-slate-400 mb-1">
                {t("deckEval.mostExpensive", {
                  defaultValue: "Most expensive cards:",
                })}
              </p>
              <div className="space-y-1" data-testid="expensive-cards-list">
                {evaluation.budget.most_expensive.map((card, i) => (
                  <div
                    key={i}
                    className="flex justify-between text-xs text-slate-300"
                  >
                    <span>
                      {card.quantity > 1 ? `${card.quantity}x ` : ""}
                      {card.name_en}
                    </span>
                    <span className="text-white font-medium">
                      R$ {card.price.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Suggestions */}
      {evaluation.suggestions.length > 0 && (
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="suggestions-section"
        >
          <h3 className="text-sm font-semibold text-white mb-2">
            {t("deckEval.suggestions", { defaultValue: "Suggestions" })}
          </h3>
          <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
            {evaluation.suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
