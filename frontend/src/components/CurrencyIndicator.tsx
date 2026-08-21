import rsFlag from "../assets/rs-flag.svg";

interface CurrencyIndicatorProps {
  currency: string;
  size?: number;
}

/**
 * Renders a currency indicator icon/symbol.
 * - PILA: RS state flag SVG
 * - BRL: "R$" text
 * - USD: "$" text
 */
export function CurrencyIndicator({
  currency,
  size = 16,
}: CurrencyIndicatorProps) {
  if (currency === "PILA") {
    return (
      <img
        src={rsFlag}
        alt="RS flag"
        width={size}
        height={Math.round(size * 0.7)}
        className="inline-block"
        data-testid="currency-indicator-pila"
      />
    );
  }

  const symbol = currency === "USD" ? "$" : "R$";
  return (
    <span
      className="font-semibold text-slate-300"
      style={{ fontSize: size * 0.75 }}
      data-testid={`currency-indicator-${currency.toLowerCase()}`}
    >
      {symbol}
    </span>
  );
}
