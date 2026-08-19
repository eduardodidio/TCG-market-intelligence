/**
 * Format a number as Brazilian Real currency (R$ 1.234,56).
 * Returns "--" for null/undefined values.
 */
export function formatBRL(value: number | null | undefined): string {
  if (value == null) return "--";
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
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
