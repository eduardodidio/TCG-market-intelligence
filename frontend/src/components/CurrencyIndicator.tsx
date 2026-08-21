import rsFlag from "../assets/rs-flag.svg";
import brFlag from "../assets/br-flag.svg";
import usFlag from "../assets/us-flag.svg";

interface CurrencyIndicatorProps {
  currency: string;
  size?: number;
}

const FLAG_MAP: Record<string, { src: string; alt: string; symbol: string }> = {
  PILA: { src: rsFlag, alt: "RS flag", symbol: "" },
  BRL: { src: brFlag, alt: "Brazil flag", symbol: "R$" },
  USD: { src: usFlag, alt: "US flag", symbol: "$" },
};

/**
 * Renders a currency indicator icon/symbol.
 * - PILA: RS state flag SVG
 * - BRL: Brazil flag + "R$"
 * - USD: US flag + "$"
 */
export function CurrencyIndicator({
  currency,
  size = 16,
}: CurrencyIndicatorProps) {
  const flagInfo = FLAG_MAP[currency];

  if (flagInfo) {
    return (
      <span
        className="inline-flex items-center gap-0.5"
        data-testid={`currency-indicator-${currency.toLowerCase()}`}
      >
        <img
          src={flagInfo.src}
          alt={flagInfo.alt}
          width={size}
          height={Math.round(size * 0.7)}
          className="inline-block"
        />
        {flagInfo.symbol && (
          <span
            className="font-semibold text-slate-400"
            style={{ fontSize: size * 0.75 }}
          >
            {flagInfo.symbol}
          </span>
        )}
      </span>
    );
  }

  // Fallback for unknown currencies
  return (
    <span
      className="font-semibold text-slate-400"
      style={{ fontSize: size * 0.75 }}
      data-testid={`currency-indicator-${currency.toLowerCase()}`}
    >
      {currency}
    </span>
  );
}
