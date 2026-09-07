import { useTranslation } from "react-i18next";

interface ArbitrageBadgeProps {
  ligaPrice: number | null;
  tcgPrice: number | null;
}

/**
 * Shows the best price source (Liga vs TCG) and gap percentage.
 * - Both prices: "Best: Liga -X%" or "Best: TCG -X%" (green)
 * - One price: "Liga only" or "TCG only" (gray)
 * - No prices: renders nothing
 */
export function ArbitrageBadge({ ligaPrice, tcgPrice }: ArbitrageBadgeProps) {
  const { t } = useTranslation();

  if (ligaPrice == null && tcgPrice == null) {
    return null;
  }

  if (ligaPrice != null && tcgPrice != null) {
    const best = ligaPrice <= tcgPrice ? "Liga" : "TCG";
    const higher = Math.max(ligaPrice, tcgPrice);
    const gapPct = higher > 0 ? (((higher - Math.min(ligaPrice, tcgPrice)) / higher) * 100).toFixed(1) : "0.0";

    return (
      <span
        className="inline-flex items-center gap-1 text-xs font-medium text-green-400 bg-green-400/10 px-1.5 py-0.5 rounded"
        data-testid="arbitrage-badge"
        title={t("arbitrage.tooltip", {
          liga: `R$ ${ligaPrice.toFixed(2)}`,
          tcg: `R$ ${tcgPrice.toFixed(2)}`,
          defaultValue: "Liga: {{liga}} | TCG: {{tcg}}",
        })}
      >
        {t("arbitrage.best", {
          source: best,
          gap: gapPct,
          defaultValue: "Best: {{source}} -{{gap}}%",
        })}
      </span>
    );
  }

  // Only one price source
  const source = ligaPrice != null ? "Liga" : "TCG";
  return (
    <span
      className="inline-flex items-center text-xs text-slate-400 bg-slate-700/50 px-1.5 py-0.5 rounded"
      data-testid="arbitrage-badge"
    >
      {t("arbitrage.sourceOnly", {
        source,
        defaultValue: "{{source}} only",
      })}
    </span>
  );
}
