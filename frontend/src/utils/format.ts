/**
 * Format a number as Brazilian Real currency (R$ 1.234,56).
 * Returns "--" for null/undefined values.
 */
export function formatBRL(value: number | string | null | undefined): string {
  if (value == null) return "--";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "--";
  return num.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Format a value in Pila currency (extenso style).
 *
 * Rules:
 * - null/undefined -> "--"
 * - Integer part uses pt-BR thousands separator (.)
 * - "pila" (singular) / "pilas" (plural, including 0)
 * - "centavo" (singular) / "centavos" (plural)
 * - Omit centavos when 0
 *
 * Examples:
 *   formatPila(230.21) -> "230 pilas e 21 centavos"
 *   formatPila(1.0)    -> "1 pila"
 *   formatPila(1.01)   -> "1 pila e 1 centavo"
 */
export function formatPila(
  value: number | string | null | undefined,
): string {
  if (value == null) return "--";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "--";

  const negative = num < 0;
  const abs = Math.abs(num);
  // Round to 2 decimal places
  const rounded = Math.round(abs * 100) / 100;
  const intPart = Math.floor(rounded);
  const centavos = Math.round((rounded - intPart) * 100);

  // Format integer with '.' as thousands separator (pt-BR)
  const formattedInt = intPart.toLocaleString("pt-BR", {
    useGrouping: true,
    maximumFractionDigits: 0,
  });

  const pilaWord = intPart === 1 ? "pila" : "pilas";
  const prefix = negative ? "-" : "";
  let result = `${prefix}${formattedInt} ${pilaWord}`;

  if (centavos > 0) {
    const centavoWord = centavos === 1 ? "centavo" : "centavos";
    result += ` e ${centavos} ${centavoWord}`;
  }

  return result;
}

/**
 * Format a number in the given currency.
 * BRL:  R$ 1.234,56 (pt-BR locale)
 * USD:  $1,234.56 (en-US locale)
 * PILA: extenso format (e.g. "230 pilas e 21 centavos")
 * Returns "--" for null/undefined values.
 */
export function formatCurrency(
  value: number | string | null | undefined,
  currency: string = "BRL",
): string {
  if (currency === "PILA") return formatPila(value);

  if (value == null) return "--";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "--";

  const locale = currency === "USD" ? "en-US" : "pt-BR";
  return num.toLocaleString(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Format a price value or return null if the price is absent/zero.
 * Use this for display contexts where 0 means "no data" (e.g. Explore Cards).
 */
export function formatPriceOrFallback(
  value: number | string | null | undefined,
  currency: string = "BRL",
): string | null {
  if (value == null) return null;
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num) || num === 0) return null;
  return formatCurrency(num, currency);
}

/**
 * Format a percentage with sign prefix.
 * Returns object with formatted string and direction for styling.
 * Example: formatPercent(12.3) -> "+12,3%"
 *          formatPercent(-5.7) -> "-5,7%"
 */
export function formatPercent(value: number): string {
  const formatted = Math.abs(value)
    .toLocaleString("pt-BR", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${formatted}%`;
}

/**
 * Format an ISO date string as DD/MM/YYYY.
 */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}
