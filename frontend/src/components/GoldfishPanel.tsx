import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchGoldfish } from "../api/decks";
import { ErrorBanner } from "./ErrorBanner";
import type { GoldfishResult } from "../types/api";

interface GoldfishPanelProps {
  deckId: number;
}

export function GoldfishPanel({ deckId }: GoldfishPanelProps) {
  const { t } = useTranslation();
  const [data, setData] = useState<GoldfishResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasFetched = useRef(false);

  const loadGoldfish = useCallback(async () => {
    setLoading(true);
    setError(null);
    const resp = await fetchGoldfish(deckId);
    if (resp.errors.length > 0) {
      setError(resp.errors[0].message);
    } else {
      setData(resp.data);
    }
    setLoading(false);
  }, [deckId]);

  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true;
      loadGoldfish();
    }
  }, [loadGoldfish]);

  if (loading) {
    return (
      <div className="space-y-4" data-testid="goldfish-loading">
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
      <ErrorBanner message={error} variant="inline" onRetry={loadGoldfish} data-testid="goldfish-error" />
    );
  }

  if (!data) return null;

  const manaChartData = data.avg_mana_by_turn.map((val, idx) => ({
    turn: idx + 1,
    mana: Number(val.toFixed(2)),
  }));

  const spellsChartData = data.avg_spells_cast_by_turn.map((val, idx) => ({
    turn: idx + 1,
    spells: Number(val.toFixed(2)),
  }));

  const qualityPct = Math.round(data.opening_hand_quality * 100);

  // Determine badge colors for screw/flood rates
  const screwPct = Math.round(data.mana_screw_rate * 100);
  const floodPct = Math.round(data.mana_flood_rate * 100);
  const screwColor =
    screwPct > 30
      ? "bg-red-900/30 text-red-400 border-red-700/50"
      : screwPct > 20
        ? "bg-orange-900/30 text-orange-400 border-orange-700/50"
        : "bg-green-900/30 text-green-400 border-green-700/50";
  const floodColor =
    floodPct > 30
      ? "bg-red-900/30 text-red-400 border-red-700/50"
      : floodPct > 20
        ? "bg-blue-900/30 text-blue-400 border-blue-700/50"
        : "bg-green-900/30 text-green-400 border-green-700/50";

  // Sort sample hands by quality for best/median/worst
  const sortedHands = [...data.sample_hands].sort(
    (a, b) => b.quality - a.quality,
  );
  const bestHand = sortedHands[0];
  const worstHand = sortedHands[sortedHands.length - 1];
  const medianHand = sortedHands[Math.floor(sortedHands.length / 2)];

  const tooltipStyle = {
    backgroundColor: "#1e293b",
    border: "1px solid #475569",
    borderRadius: "0.375rem",
  };

  return (
    <div className="space-y-6" data-testid="goldfish-panel">
      {/* Title */}
      <div>
        <h2 className="text-lg font-bold text-white">
          {t("decks.goldfish.title")}
        </h2>
        <p className="text-sm text-slate-400">
          {t("decks.goldfish.subtitle")}
        </p>
      </div>

      {/* Opening Hand Quality + Screw/Flood */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Opening Hand Quality */}
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="opening-hand-quality-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("decks.goldfish.openingHandQuality")}
          </h3>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="w-full bg-slate-700 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all ${
                    qualityPct >= 70
                      ? "bg-green-500"
                      : qualityPct >= 50
                        ? "bg-yellow-500"
                        : qualityPct >= 30
                          ? "bg-orange-500"
                          : "bg-red-500"
                  }`}
                  style={{ width: `${qualityPct}%` }}
                  data-testid="quality-bar"
                />
              </div>
            </div>
            <span
              className={`text-lg font-bold ${
                qualityPct >= 70
                  ? "text-green-400"
                  : qualityPct >= 50
                    ? "text-yellow-400"
                    : qualityPct >= 30
                      ? "text-orange-400"
                      : "text-red-400"
              }`}
              data-testid="quality-value"
            >
              {qualityPct}%
            </span>
          </div>
        </div>

        {/* Screw & Flood Rates */}
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="screw-flood-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("decks.goldfish.screwRate")} / {t("decks.goldfish.floodRate")}
          </h3>
          <div className="flex gap-3">
            <span
              className={`inline-flex items-center px-3 py-1.5 rounded text-sm font-medium border ${screwColor}`}
              data-testid="screw-rate-badge"
            >
              {t("decks.goldfish.screwRate")}: {screwPct}%
            </span>
            <span
              className={`inline-flex items-center px-3 py-1.5 rounded text-sm font-medium border ${floodColor}`}
              data-testid="flood-rate-badge"
            >
              {t("decks.goldfish.floodRate")}: {floodPct}%
            </span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mana by Turn LineChart */}
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="mana-by-turn-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("decks.goldfish.manaByTurn")}
          </h3>
          {manaChartData.length > 0 ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={manaChartData}>
                  <XAxis
                    dataKey="turn"
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={30}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    labelStyle={{ color: "#94a3b8" }}
                    labelFormatter={(v) => t("decks.goldfish.turn", { n: v })}
                  />
                  <Line
                    type="monotone"
                    dataKey="mana"
                    stroke="#22d3ee"
                    strokeWidth={2}
                    dot={{ fill: "#22d3ee", r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 text-center py-8">
              {t("deckEval.noData", { defaultValue: "No data" })}
            </p>
          )}
        </div>

        {/* Spells by Turn BarChart */}
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="spells-by-turn-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("decks.goldfish.spellsByTurn")}
          </h3>
          {spellsChartData.length > 0 ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={spellsChartData}>
                  <XAxis
                    dataKey="turn"
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
                    contentStyle={tooltipStyle}
                    labelStyle={{ color: "#94a3b8" }}
                    labelFormatter={(v) => t("decks.goldfish.turn", { n: v })}
                  />
                  <Bar dataKey="spells" fill="#a855f7" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 text-center py-8">
              {t("deckEval.noData", { defaultValue: "No data" })}
            </p>
          )}
        </div>
      </div>

      {/* Sample Hands */}
      {sortedHands.length > 0 && (
        <div
          className="p-4 rounded-lg bg-slate-800 border border-slate-600"
          data-testid="sample-hands-section"
        >
          <h3 className="text-sm font-semibold text-white mb-3">
            {t("decks.goldfish.sampleHands")}
          </h3>
          <div className="space-y-4">
            {bestHand && (
              <SampleHandRow
                label={t("decks.goldfish.bestHand")}
                hand={bestHand}
                labelColor="text-green-400"
                t={t}
              />
            )}
            {medianHand && medianHand !== bestHand && medianHand !== worstHand && (
              <SampleHandRow
                label={t("decks.goldfish.medianHand")}
                hand={medianHand}
                labelColor="text-yellow-400"
                t={t}
              />
            )}
            {worstHand && worstHand !== bestHand && (
              <SampleHandRow
                label={t("decks.goldfish.worstHand")}
                hand={worstHand}
                labelColor="text-red-400"
                t={t}
              />
            )}
          </div>
        </div>
      )}

      {/* Footer: Simulate Again + info */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <button
          onClick={() => loadGoldfish()}
          className="inline-flex items-center gap-2 rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors"
          data-testid="simulate-again-btn"
        >
          {t("decks.goldfish.simulateAgain")}
        </button>
        <p className="text-xs text-slate-500" data-testid="simulation-info">
          {t("decks.goldfish.simulations", { count: data.total_simulations })}
        </p>
      </div>
    </div>
  );
}

function SampleHandRow({
  label,
  hand,
  labelColor,
  t,
}: {
  label: string;
  hand: { cards: string[]; quality: number; land_count: number };
  labelColor: string;
  t: (key: string, opts?: Record<string, unknown>) => string;
}) {
  const qualityPct = Math.round(hand.quality * 100);
  return (
    <div data-testid={`sample-hand-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs font-semibold ${labelColor}`}>{label}</span>
        <span className="text-xs text-slate-500">
          {t("decks.goldfish.quality", { pct: qualityPct })}
        </span>
        <span className="text-xs text-slate-500">
          {t("decks.goldfish.lands", { count: hand.land_count })}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {hand.cards.map((card, idx) => (
          <span
            key={idx}
            className="inline-block px-2 py-0.5 rounded bg-slate-700 text-xs text-slate-300 truncate max-w-[200px]"
            title={card}
          >
            {card}
          </span>
        ))}
      </div>
    </div>
  );
}
